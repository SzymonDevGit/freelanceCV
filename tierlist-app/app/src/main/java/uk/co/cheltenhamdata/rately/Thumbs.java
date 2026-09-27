package uk.co.cheltenhamdata.rately;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.Handler;
import android.os.Looper;
import android.util.LruCache;
import android.widget.ImageView;

import java.io.File;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Loads saved pictures off the main thread, with a memory cache so boards scroll smoothly. */
final class Thumbs {

    private static final LruCache<String, Bitmap> cache = new LruCache<String, Bitmap>(
            (int) Math.min(Runtime.getRuntime().maxMemory() / 6, 96L << 20)) {
        @Override protected int sizeOf(String key, Bitmap b) {
            return b.getByteCount();
        }
    };
    private static final ExecutorService pool = Executors.newFixedThreadPool(2);
    private static final Handler main = new Handler(Looper.getMainLooper());

    private Thumbs() {}

    /** Shows the picture in the view; sizePx is how big it is drawn. */
    static void into(final ImageView view, File file, int sizePx) {
        final int want = bucket(sizePx);
        final String key = key(file, want);
        view.setTag(key);
        Bitmap hit = cache.get(key);
        if (hit != null) {
            view.setImageBitmap(hit);
            return;
        }
        view.setImageDrawable(null);
        load(file, want, new Runnable() {
            @Override public void run() {
                Bitmap b = cache.get(key);
                if (b != null && key.equals(view.getTag())) view.setImageBitmap(b);
            }
        });
    }

    /** Warms the cache so the next quick-rate card appears instantly. */
    static void prefetch(File file, int sizePx) {
        int want = bucket(sizePx);
        if (cache.get(key(file, want)) == null) load(file, want, null);
    }

    private static void load(final File file, final int want, final Runnable done) {
        pool.execute(new Runnable() {
            @Override public void run() {
                String key = key(file, want);
                if (cache.get(key) == null) {
                    Bitmap b = decode(file, want);
                    if (b != null) cache.put(key, b);
                }
                if (done != null) main.post(done);
            }
        });
    }

    private static int bucket(int px) {
        return px <= 200 ? 200 : px <= 400 ? 400 : 800;
    }

    private static String key(File f, int want) {
        return f.getName() + "@" + want;
    }

    private static Bitmap decode(File f, int want) {
        BitmapFactory.Options o = new BitmapFactory.Options();
        o.inJustDecodeBounds = true;
        BitmapFactory.decodeFile(f.getAbsolutePath(), o);
        if (o.outWidth <= 0) return null;
        int sample = 1;
        while (Math.min(o.outWidth, o.outHeight) / (sample * 2) >= want) sample *= 2;
        BitmapFactory.Options d = new BitmapFactory.Options();
        d.inSampleSize = sample;
        if (want <= 200) d.inPreferredConfig = Bitmap.Config.RGB_565;
        return BitmapFactory.decodeFile(f.getAbsolutePath(), d);
    }
}
