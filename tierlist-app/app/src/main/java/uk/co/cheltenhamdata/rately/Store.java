package uk.co.cheltenhamdata.rately;

import android.content.Context;
import android.util.AtomicFile;
import android.util.Log;

import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;

/**
 * Keeps every tier list in memory and on disk. Each list is one JSON file in
 * files/lists/, written atomically after every change; the cropped pictures are
 * JPEGs in files/images/.
 */
final class Store {

    private static final String TAG = "Rately";
    private static final HashMap<String, TierList> cache = new HashMap<>();
    private static boolean scanned;

    private Store() {}

    static File imagesDir(Context c) {
        File d = new File(c.getFilesDir(), "images");
        if (!d.isDirectory() && !d.mkdirs()) Log.w(TAG, "could not create " + d);
        return d;
    }

    static File image(Context c, String name) {
        return new File(imagesDir(c), name);
    }

    private static File listsDir(Context c) {
        File d = new File(c.getFilesDir(), "lists");
        if (!d.isDirectory() && !d.mkdirs()) Log.w(TAG, "could not create " + d);
        return d;
    }

    private static File file(Context c, String id) {
        return new File(listsDir(c), id + ".json");
    }

    /** All lists, most recently changed first. */
    static synchronized List<TierList> all(Context c) {
        if (!scanned) {
            File[] files = listsDir(c).listFiles();
            if (files != null) {
                for (File f : files) {
                    String n = f.getName();
                    if (!n.endsWith(".json")) continue;
                    String id = n.substring(0, n.length() - 5);
                    if (cache.containsKey(id)) continue;
                    TierList l = read(f);
                    if (l != null) cache.put(l.id, l);
                }
            }
            scanned = true;
        }
        ArrayList<TierList> out = new ArrayList<>(cache.values());
        Collections.sort(out, new Comparator<TierList>() {
            @Override public int compare(TierList a, TierList b) {
                return Long.compare(b.updated, a.updated);
            }
        });
        return out;
    }

    static synchronized TierList get(Context c, String id) {
        if (id == null) return null;
        TierList l = cache.get(id);
        if (l == null && !scanned) {
            l = read(file(c, id));
            if (l != null) cache.put(id, l);
        }
        return l;
    }

    static synchronized TierList create(Context c, String name) {
        TierList l = TierList.create(name);
        cache.put(l.id, l);
        write(c, l);
        return l;
    }

    /** Saves after a change, which also moves the list to the top of the home screen. */
    static synchronized void save(Context c, TierList l) {
        l.updated = System.currentTimeMillis();
        write(c, l);
    }

    /** Saves without bumping the list's last-changed time. */
    static synchronized void flush(Context c, TierList l) {
        if (cache.get(l.id) == l) write(c, l);
    }

    static synchronized void delete(Context c, TierList l) {
        for (TierList.Item it : l.allItems()) deleteImage(c, it);
        new AtomicFile(file(c, l.id)).delete();
        cache.remove(l.id);
    }

    static void deleteImage(Context c, TierList.Item it) {
        File f = image(c, it.image);
        if (f.exists() && !f.delete()) Log.w(TAG, "could not delete " + f);
    }

    private static void write(Context c, TierList l) {
        AtomicFile af = new AtomicFile(file(c, l.id));
        FileOutputStream out = null;
        try {
            out = af.startWrite();
            out.write(l.toJson().toString().getBytes("UTF-8"));
            af.finishWrite(out);
        } catch (Exception e) {
            if (out != null) af.failWrite(out);
            Log.e(TAG, "could not save " + l.id, e);
        }
    }

    private static TierList read(File f) {
        try {
            byte[] bytes = new AtomicFile(f).readFully();
            return TierList.fromJson(new JSONObject(new String(bytes, "UTF-8")));
        } catch (Exception e) {
            Log.e(TAG, "could not read " + f, e);
            return null;
        }
    }
}
