package uk.co.cheltenhamdata.rately;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Crops each picked photo to a square, one at a time, optionally with text
 * over it, then adds them to the list's to-rate pile. "Auto-crop the rest"
 * centre-crops everything left.
 */
public class CropActivity extends Activity {

    static final String EXTRA_ID = "list";
    static final String EXTRA_URIS = "uris";
    static final String RESULT_ADDED = "added";
    private static final int REQ_CAPTION = 1;

    private TierList list;
    private ArrayList<Uri> uris;
    private int index;
    private int added;
    private boolean busy;
    /** Text for the photo being cropped now, saved with it on "Use". */
    private Caption pending;

    private CropView crop;
    private TextView title;
    private TextView status;
    private TextView use;
    private TextView skip;
    private TextView auto;
    private TextView text;
    private View rotate;

    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        list = Store.get(this, getIntent().getStringExtra(EXTRA_ID));
        uris = getIntent().getParcelableArrayListExtra(EXTRA_URIS);
        if (list == null || uris == null || uris.isEmpty()) {
            finish();
            return;
        }
        if (state != null) {
            index = state.getInt("index");
            added = state.getInt("added");
            pending = Caption.fromJson(state.getString("caption"));
        }
        getWindow().setStatusBarColor(Toon.DUSK);
        getWindow().setNavigationBarColor(Toon.DUSK);
        setContentView(build());
        load();
    }

    @Override protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        out.putInt("index", index);
        out.putInt("added", added);
        if (pending != null) out.putString("caption", pending.toJsonString());
    }

    @Override protected void onDestroy() {
        super.onDestroy();
        worker.shutdown();
    }

    @Override public void onBackPressed() {
        finishWithResult();
    }

    private int dp(float v) {
        return Toon.dp(this, v);
    }

    private View build() {
        LinearLayout root = Toon.column(this);
        root.setBackgroundColor(Toon.DUSK);
        root.setPadding(dp(16), dp(12), dp(16), dp(18));

        LinearLayout bar = Toon.row(this);
        ImageView close = Toon.iconButton(this, Icon.CLOSE, Toon.CREAM, 46);
        close.setContentDescription("Stop cropping");
        close.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { finishWithResult(); }
        });
        bar.addView(close, Toon.lp(dp(48), dp(48)));
        title = Toon.text(this, "", 22, Toon.CREAM, true);
        title.setPadding(dp(14), 0, 0, 0);
        bar.addView(title, Toon.lp(0, -2, 1));
        root.addView(bar);

        crop = new CropView(this);
        root.addView(crop, Toon.lp(-1, 0, 1));

        status = Toon.text(this, "Pinch and drag to frame it", 16, Toon.LILAC, false);
        status.setGravity(Gravity.CENTER);
        status.setPadding(0, 0, 0, dp(14));
        root.addView(status, Toon.lp(-1, -2));

        LinearLayout row1 = Toon.row(this);
        rotate = Toon.iconButton(this, Icon.ROTATE, Toon.LILAC, 56);
        rotate.setContentDescription("Rotate");
        rotate.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { crop.rotate(); }
        });
        row1.addView(rotate, Toon.margins(Toon.lp(dp(58), dp(58)), 0, 0, dp(10), 0));
        text = Toon.button(this, "", Toon.LILAC);
        text.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { editCaption(); }
        });
        row1.addView(text, Toon.margins(Toon.lp(0, -2, 1.3f), 0, 0, dp(10), 0));
        skip = Toon.button(this, "Skip", Toon.LILAC);
        skip.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { next(); }
        });
        row1.addView(skip, Toon.lp(0, -2, 1));
        root.addView(row1, Toon.lp(-1, -2));

        auto = Toon.button(this, "", Toon.PEACH);
        auto.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { autoRest(); }
        });
        root.addView(auto, Toon.margins(Toon.lp(-1, -2), 0, dp(10), 0, 0));

        use = Toon.button(this, "", Toon.SUN);
        use.setTextSize(20);
        Toon.withIcon(this, use, Icon.CHECK, "Use this crop");
        use.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { useCrop(); }
        });
        root.addView(use, Toon.margins(Toon.lp(-1, -2), 0, dp(10), 0, 0));
        return root;
    }

    private void setBusy(boolean b) {
        busy = b;
        use.setEnabled(!b);
        skip.setEnabled(!b);
        auto.setEnabled(!b);
        text.setEnabled(!b);
        rotate.setEnabled(!b);
        crop.setEnabled(!b);
    }

    private void load() {
        if (index >= uris.size()) {
            finishWithResult();
            return;
        }
        int left = uris.size() - index - 1;
        title.setText(uris.size() == 1 ? "Crop your picture" : "Crop " + (index + 1) + " of " + uris.size());
        auto.setVisibility(left > 0 ? View.VISIBLE : View.GONE);
        auto.setText("Use this + auto-crop " + left + " more");
        status.setText("Pinch and drag to frame it");
        showCaption();
        crop.setBitmap(null);
        crop.setMessage("Loading…");
        setBusy(true);
        final Uri uri = uris.get(index);
        final int at = index;
        worker.execute(new Runnable() {
            @Override public void run() {
                Bitmap b = null;
                try {
                    b = Images.load(CropActivity.this, uri);
                } catch (Exception | OutOfMemoryError e) {
                    Log.w("Rately", "could not open " + uri, e);
                }
                final Bitmap loaded = b;
                main.post(new Runnable() {
                    @Override public void run() {
                        if (isFinishing() || at != index) return;
                        if (loaded == null) {
                            Toon.toast(CropActivity.this, "Couldn’t open that picture, skipping it");
                            next();
                            return;
                        }
                        crop.setBitmap(loaded);
                        setBusy(false);
                    }
                });
            }
        });
    }

    private void next() {
        index++;
        pending = null;
        load();
    }

    private void showCaption() {
        crop.setCaption(pending);
        Toon.withIcon(this, text, Icon.TEXT, pending == null ? "Add text" : "Edit text");
    }

    /** Opens the text editor on a snapshot of the current crop. */
    private void editCaption() {
        if (busy || crop.getBitmap() == null) return;
        File snapshot = new File(getCacheDir(), "caption-preview.jpg");
        OutputStream out = null;
        try {
            out = new FileOutputStream(snapshot);
            crop.crop(Images.OUT_SIZE).compress(Bitmap.CompressFormat.JPEG, 85, out);
        } catch (IOException e) {
            Log.w("Rately", "could not write preview", e);
            return;
        } finally {
            Images.close(out);
        }
        Intent i = new Intent(this, CaptionActivity.class)
                .putExtra(CaptionActivity.EXTRA_IMAGE, snapshot.getAbsolutePath());
        if (pending != null) i.putExtra(CaptionActivity.EXTRA_CAPTION, pending.toJsonString());
        startActivityForResult(i, REQ_CAPTION);
    }

    @Override protected void onActivityResult(int req, int result, Intent data) {
        super.onActivityResult(req, result, data);
        if (req != REQ_CAPTION || result != RESULT_OK || data == null) return;
        pending = Caption.fromJson(data.getStringExtra(CaptionActivity.EXTRA_CAPTION));
        showCaption();
    }

    private void useCrop() {
        if (busy || crop.getBitmap() == null) return;
        final Bitmap out = crop.crop(Images.OUT_SIZE);
        final Caption cap = pending;
        setBusy(true);
        worker.execute(new Runnable() {
            @Override public void run() {
                final String name = save(out);
                main.post(new Runnable() {
                    @Override public void run() {
                        if (name != null) addToQueue(name, cap);
                        next();
                    }
                });
            }
        });
    }

    /** Saves the current crop, then centre-crops every remaining photo. */
    private void autoRest() {
        if (busy || crop.getBitmap() == null) return;
        final Bitmap first = crop.crop(Images.OUT_SIZE);
        final Caption cap = pending;
        final ArrayList<Uri> rest = new ArrayList<>(uris.subList(index + 1, uris.size()));
        setBusy(true);
        worker.execute(new Runnable() {
            @Override public void run() {
                post(save(first), cap, -1, rest.size());
                for (int i = 0; i < rest.size(); i++) {
                    String name = null;
                    try {
                        Bitmap b = Images.load(CropActivity.this, rest.get(i));
                        if (b != null) {
                            Bitmap sq = Images.centerCrop(b, Images.OUT_SIZE);
                            b.recycle();
                            name = save(sq);
                            sq.recycle();
                        }
                    } catch (Exception | OutOfMemoryError e) {
                        Log.w("Rately", "could not auto-crop " + rest.get(i), e);
                    }
                    post(name, null, i, rest.size());
                }
                main.post(new Runnable() {
                    @Override public void run() {
                        index = uris.size();
                        finishWithResult();
                    }
                });
            }

            private void post(final String name, final Caption c, final int i, final int n) {
                main.post(new Runnable() {
                    @Override public void run() {
                        if (name != null) addToQueue(name, c);
                        if (i >= 0) status.setText("Auto-cropping " + (i + 1) + " of " + n + "…");
                    }
                });
            }
        });
    }

    private String save(Bitmap b) {
        try {
            return Images.save(this, b);
        } catch (Exception e) {
            Log.w("Rately", "could not save crop", e);
            return null;
        }
    }

    private void addToQueue(String image, Caption caption) {
        TierList.Item it = TierList.newItem(image);
        it.caption = caption;
        list.queue.add(it);
        Store.save(this, list);
        added++;
    }

    private void finishWithResult() {
        setResult(RESULT_OK, new Intent().putExtra(RESULT_ADDED, added));
        finish();
    }
}
