package uk.co.cheltenhamdata.rately;

import android.app.Activity;
import android.content.Context;
import android.graphics.drawable.Drawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.HapticFeedbackConstants;
import android.view.View;
import android.view.animation.AccelerateInterpolator;
import android.view.animation.OvershootInterpolator;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.ArrayList;

/**
 * Quick rating: one big card at a time. Tap a tier and the card flies into it
 * while the next one pops up, so a whole pile can be rated in seconds.
 */
public class RateActivity extends Activity {

    static final String EXTRA_ID = "list";

    private TierList list;
    private FrameLayout root;
    private FrameLayout stage;
    private SquareFrame card;
    private ThumbView photo;
    private TextView progress;
    private ImageView undoButton;
    private TextView skipButton;
    private LinearLayout buttons;
    private View done;
    private int photoPx;
    private int rated;
    private int tilt = 1;
    /** Ids of the pictures rated on this screen, most recent last. */
    private final ArrayList<String> history = new ArrayList<>();

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        list = Store.get(this, getIntent().getStringExtra(EXTRA_ID));
        if (list == null) {
            finish();
            return;
        }
        if (state != null) {
            rated = state.getInt("rated");
            ArrayList<String> h = state.getStringArrayList("history");
            if (h != null) history.addAll(h);
        }
        getWindow().setStatusBarColor(0xFF3B335A);
        getWindow().setNavigationBarColor(0xFF9C8A52);
        photoPx = getResources().getDisplayMetrics().widthPixels;
        setContentView(build());
        show(false);
    }

    @Override protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        out.putInt("rated", rated);
        out.putStringArrayList("history", history);
    }

    @Override protected void onPause() {
        super.onPause();
        if (list != null) Store.flush(this, list);
    }

    private int dp(float v) {
        return Toon.dp(this, v);
    }

    private View build() {
        root = new FrameLayout(this);
        SunsetView scene = new SunsetView(this);
        scene.setHorizon(0.64f);
        scene.setTent(false, 0);
        root.addView(scene, new FrameLayout.LayoutParams(-1, -1));

        LinearLayout col = Toon.column(this);
        col.setPadding(dp(16), dp(12), dp(16), dp(18));

        LinearLayout bar = Toon.row(this);
        ImageView close = Toon.iconButton(this, Icon.CLOSE, Toon.CREAM, 46);
        close.setContentDescription("Close");
        close.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { finish(); }
        });
        bar.addView(close, Toon.lp(dp(48), dp(48)));
        progress = Toon.text(this, "", 18, Toon.INK, true);
        progress.setGravity(Gravity.CENTER);
        progress.setBackground(new ToonDrawable(Toon.CREAM, dp(18), dp(3), dp(3)));
        progress.setPadding(dp(16), dp(7), dp(19), dp(10));
        LinearLayout.LayoutParams plp = Toon.lp(-2, -2);
        plp.gravity = Gravity.CENTER;
        LinearLayout mid = Toon.row(this);
        mid.setGravity(Gravity.CENTER);
        mid.addView(progress, plp);
        bar.addView(mid, Toon.lp(0, -2, 1));
        undoButton = Toon.iconButton(this, Icon.UNDO, Toon.CREAM, 46);
        undoButton.setContentDescription("Undo");
        undoButton.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { undo(); }
        });
        bar.addView(undoButton, Toon.lp(dp(48), dp(48)));
        col.addView(bar);

        stage = new FrameLayout(this);
        stage.setClipChildren(false);
        card = new SquareFrame(this);
        int shadow = dp(6);
        card.setBackground(new ToonDrawable(Toon.CREAM, dp(26), shadow, dp(3.5f)));
        card.setPadding(dp(12), dp(12), dp(12) + shadow, dp(12) + shadow);
        photo = new ThumbView(this, dp(16), dp(3));
        card.addView(photo, new FrameLayout.LayoutParams(-1, -1));
        stage.addView(card, new FrameLayout.LayoutParams(-2, -2, Gravity.CENTER));
        done = buildDone();
        stage.addView(done, new FrameLayout.LayoutParams(-1, -2, Gravity.CENTER));
        col.addView(stage, Toon.margins(Toon.lp(-1, 0, 1), 0, dp(14), 0, dp(6)));

        skipButton = Toon.text(this, "Skip", 17, Toon.CREAM, true);
        skipButton.setShadowLayer(0.01f, 0, dp(2), Toon.INK);
        skipButton.setGravity(Gravity.CENTER);
        skipButton.setPadding(dp(16), dp(8), dp(16), dp(12));
        Icon next = new Icon(Icon.NEXT, Toon.CREAM, dp(20));
        next.setBounds(0, 0, next.getIntrinsicWidth(), next.getIntrinsicHeight());
        skipButton.setCompoundDrawablesRelative(null, null, next, null);
        skipButton.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { skip(); }
        });
        LinearLayout.LayoutParams slp = Toon.lp(-2, -2);
        slp.gravity = Gravity.CENTER_HORIZONTAL;
        col.addView(skipButton, slp);

        buttons = Toon.column(this);
        buildTierButtons();
        col.addView(buttons, Toon.lp(-1, -2));

        root.addView(col, new FrameLayout.LayoutParams(-1, -1));
        return root;
    }

    private void buildTierButtons() {
        buttons.removeAllViews();
        int n = list.tiers.size();
        int cols = n <= 3 ? n : n == 4 ? 2 : n <= 6 ? 3 : 4;
        int rows = (n + cols - 1) / cols;
        int height = rows <= 2 ? dp(70) : dp(58);
        float big = rows <= 2 ? 34 : 28;
        LinearLayout row = null;
        for (int i = 0; i < n; i++) {
            if (i % cols == 0) {
                row = Toon.row(this);
                buttons.addView(row, Toon.margins(Toon.lp(-1, -2), 0, i == 0 ? 0 : dp(10), 0, 0));
            }
            final TierList.Tier t = list.tiers.get(i);
            String label = t.shownLabel();
            final TextView b = Toon.button(this, label, t.color);
            b.setTextSize(Toon.labelSize(label, big));
            b.setMaxLines(2);
            b.setMinHeight(height);
            b.setPadding(dp(6), dp(6), dp(10), dp(10));
            b.setOnClickListener(new View.OnClickListener() {
                @Override public void onClick(View v) { rate(t, b); }
            });
            boolean last = i % cols == cols - 1;
            row.addView(b, Toon.margins(Toon.lp(0, height, 1), 0, 0, last ? 0 : dp(10), 0));
        }
        // Keep the last row's buttons the same width as the others.
        if (row != null) {
            for (int i = row.getChildCount(); i < cols; i++) {
                View spacer = new View(this);
                row.addView(spacer, Toon.margins(Toon.lp(0, height, 1), i == 0 ? 0 : dp(10), 0, 0, 0));
            }
        }
    }

    private View buildDone() {
        LinearLayout box = Toon.column(this);
        box.setGravity(Gravity.CENTER_HORIZONTAL);
        ToonText title = new ToonText(this, "All rated!", 46, Toon.SUN);
        box.addView(title);
        TextView msg = Toon.text(this, "Nice one. Your tier list is saved.", 18, Toon.CREAM, true);
        msg.setShadowLayer(0.01f, 0, dp(2), Toon.INK);
        msg.setGravity(Gravity.CENTER);
        msg.setPadding(0, dp(6), 0, dp(20));
        box.addView(msg);
        TextView see = Toon.button(this, "See the board", Toon.SUN);
        see.setPadding(dp(24), dp(12), dp(28), dp(16));
        see.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { finish(); }
        });
        box.addView(see, Toon.lp(-2, -2));
        return box;
    }

    /** Shows the card for the first picture in the queue, or the finished state. */
    private void show(boolean animate) {
        int total = rated + list.queue.size();
        progress.setText(Math.min(rated + 1, total) + " / " + total);
        undoButton.setEnabled(!history.isEmpty());
        boolean finished = list.queue.isEmpty();
        done.setVisibility(finished ? View.VISIBLE : View.GONE);
        card.setVisibility(finished ? View.INVISIBLE : View.VISIBLE);
        skipButton.setVisibility(finished || list.queue.size() < 2 ? View.INVISIBLE : View.VISIBLE);
        setButtonsEnabled(!finished);
        if (finished) {
            progress.setText(total + " / " + total);
            if (animate) {
                done.setScaleX(0.6f);
                done.setScaleY(0.6f);
                done.animate().scaleX(1).scaleY(1).setInterpolator(new OvershootInterpolator(2.5f))
                        .setDuration(320).start();
            }
            return;
        }
        Thumbs.into(photo, Store.image(this, list.queue.get(0).image), photoPx);
        photo.setCaption(list.queue.get(0).caption);
        for (int i = 1; i < Math.min(3, list.queue.size()); i++) {
            Thumbs.prefetch(Store.image(this, list.queue.get(i).image), photoPx);
        }
        tilt = -tilt;
        card.animate().cancel();
        card.setRotation(tilt * 1.6f);
        if (animate) {
            card.setScaleX(0.82f);
            card.setScaleY(0.82f);
            card.setAlpha(0.4f);
            card.animate().scaleX(1).scaleY(1).alpha(1).setInterpolator(new OvershootInterpolator(2f))
                    .setDuration(220).start();
        } else {
            card.setScaleX(1);
            card.setScaleY(1);
            card.setAlpha(1);
        }
    }

    private void setButtonsEnabled(boolean on) {
        for (int r = 0; r < buttons.getChildCount(); r++) {
            LinearLayout row = (LinearLayout) buttons.getChildAt(r);
            for (int i = 0; i < row.getChildCount(); i++) row.getChildAt(i).setEnabled(on);
        }
    }

    private void rate(TierList.Tier t, View button) {
        if (list.queue.isEmpty()) return;
        TierList.Item it = list.queue.get(0);
        flyTo(button);
        list.move(it, t, t.items.size());
        Store.save(this, list);
        history.add(it.id);
        rated++;
        button.performHapticFeedback(HapticFeedbackConstants.VIRTUAL_KEY);
        button.animate().cancel();
        button.setScaleX(1.12f);
        button.setScaleY(1.12f);
        button.animate().scaleX(1).scaleY(1).setDuration(180).start();
        show(true);
    }

    /** A copy of the current card shrinks into the tapped button, so taps are never blocked. */
    private void flyTo(View target) {
        Drawable d = photo.getDrawable();
        if (d == null) return;
        final ThumbView ghost = new ThumbView(this, dp(16), dp(3));
        ghost.setImageDrawable(d.getConstantState() != null ? d.getConstantState().newDrawable() : d);
        ghost.setCaption(photo.getCaption());
        int[] rootAt = new int[2];
        int[] photoAt = new int[2];
        int[] targetAt = new int[2];
        root.getLocationInWindow(rootAt);
        photo.getLocationInWindow(photoAt);
        target.getLocationInWindow(targetAt);
        int w = photo.getWidth();
        int h = photo.getHeight();
        root.addView(ghost, new FrameLayout.LayoutParams(w, h));
        float x = photoAt[0] - rootAt[0];
        float y = photoAt[1] - rootAt[1];
        ghost.setX(x);
        ghost.setY(y);
        ghost.setRotation(card.getRotation());
        float tx = targetAt[0] - rootAt[0] + target.getWidth() / 2f - w / 2f;
        float ty = targetAt[1] - rootAt[1] + target.getHeight() / 2f - h / 2f;
        ghost.animate().x(tx).y(ty).scaleX(0.14f).scaleY(0.14f).rotation(tilt * 28).alpha(0.3f)
                .setInterpolator(new AccelerateInterpolator(1.2f)).setDuration(280)
                .withEndAction(new Runnable() {
                    @Override public void run() { root.removeView(ghost); }
                }).start();
    }

    private void skip() {
        if (list.queue.size() < 2) return;
        TierList.Item it = list.queue.remove(0);
        list.queue.add(it);
        Store.save(this, list);
        show(true);
    }

    private void undo() {
        while (!history.isEmpty()) {
            String id = history.remove(history.size() - 1);
            TierList.Item it = list.findItem(id);
            if (it == null || list.tierOf(it) == null) continue;
            list.move(it, null, 0);
            Store.save(this, list);
            rated = Math.max(0, rated - 1);
            show(true);
            return;
        }
        undoButton.setEnabled(false);
    }

    /** A FrameLayout that stays square, as big as the space it is given allows. */
    static final class SquareFrame extends FrameLayout {
        SquareFrame(Context c) {
            super(c);
        }

        @Override protected void onMeasure(int ws, int hs) {
            int w = MeasureSpec.getSize(ws);
            int h = MeasureSpec.getSize(hs);
            int side = Math.min(w, h);
            int spec = MeasureSpec.makeMeasureSpec(side, MeasureSpec.EXACTLY);
            super.onMeasure(spec, spec);
        }
    }
}
