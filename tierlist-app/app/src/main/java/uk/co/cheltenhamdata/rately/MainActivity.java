package uk.co.cheltenhamdata.rately;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.os.Bundle;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.List;

/** Home: the sunset header and a card for every tier list. */
public class MainActivity extends Activity {

    private LinearLayout cards;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(0xFF3B335A);
        getWindow().setNavigationBarColor(Toon.NIGHT);

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Toon.DUSK);

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        LinearLayout content = Toon.column(this);
        scroll.addView(content);

        FrameLayout header = new FrameLayout(this);
        SunsetView scene = new SunsetView(this);
        scene.setHorizon(0.6f);
        scene.setTent(true, 0.24f);
        header.addView(scene, new FrameLayout.LayoutParams(-1, -1));
        LinearLayout titles = Toon.column(this);
        titles.setPadding(dp(22), dp(30), dp(22), 0);
        titles.addView(new ToonText(this, getString(R.string.app_name), 54, Toon.CREAM));
        TextView tagline = Toon.text(this, "Rate anything. Fast.", 18, Toon.CREAM, true);
        tagline.setShadowLayer(0.01f, 0, dp(2), Toon.INK);
        tagline.setPadding(dp(4), dp(2), 0, 0);
        titles.addView(tagline);
        header.addView(titles, new FrameLayout.LayoutParams(-1, -2));
        content.addView(header, Toon.lp(-1, dp(280)));

        TextView section = Toon.text(this, "YOUR TIER LISTS", 14, Toon.LILAC, true);
        section.setLetterSpacing(0.12f);
        section.setPadding(dp(20), dp(20), dp(20), dp(12));
        content.addView(section);

        cards = Toon.column(this);
        cards.setPadding(dp(16), 0, dp(16), dp(120));
        content.addView(cards, Toon.lp(-1, -2));

        root.addView(scroll, new FrameLayout.LayoutParams(-1, -1));

        TextView add = Toon.button(this, "", Toon.SUN);
        add.setTextSize(20);
        Toon.withIcon(this, add, Icon.PLUS, "New tier list");
        add.setPadding(dp(26), dp(14), dp(30), dp(18));
        add.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { newList(); }
        });
        FrameLayout.LayoutParams addLp = new FrameLayout.LayoutParams(-2, -2,
                Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL);
        addLp.bottomMargin = dp(22);
        root.addView(add, addLp);

        setContentView(root);
    }

    @Override protected void onResume() {
        super.onResume();
        render();
    }

    private int dp(float v) {
        return Toon.dp(this, v);
    }

    private void render() {
        cards.removeAllViews();
        List<TierList> all = Store.all(this);
        if (all.isEmpty()) {
            cards.addView(emptyCard(), Toon.lp(-1, -2));
            return;
        }
        for (TierList l : all) {
            cards.addView(card(l), Toon.margins(Toon.lp(-1, -2), 0, 0, 0, dp(14)));
        }
    }

    private View emptyCard() {
        LinearLayout box = Toon.column(this);
        box.setGravity(Gravity.CENTER_HORIZONTAL);
        int shadow = dp(5);
        box.setBackground(new ToonDrawable(Toon.CREAM, dp(20), shadow, dp(3)));
        box.setPadding(dp(20), dp(22), dp(20) + shadow, dp(22) + shadow);
        TextView t = Toon.text(this, "No tier lists yet", 22, Toon.INK, true);
        t.setGravity(Gravity.CENTER);
        box.addView(t);
        TextView m = Toon.text(this, "Tap New tier list, add some pictures and start rating.", 16,
                Toon.MUTED, false);
        m.setGravity(Gravity.CENTER);
        m.setLineSpacing(0, 1.15f);
        m.setPadding(0, dp(8), 0, 0);
        box.addView(m);
        return box;
    }

    private View card(final TierList l) {
        LinearLayout box = Toon.column(this);
        int shadow = dp(5);
        box.setBackground(new ToonDrawable(Toon.CREAM, dp(20), shadow, dp(3)));
        box.setPadding(dp(16), dp(14), dp(16) + shadow, dp(16) + shadow);

        LinearLayout top = Toon.row(this);
        TextView name = Toon.text(this, l.name, 22, Toon.INK, true);
        name.setSingleLine(true);
        name.setEllipsize(TextUtils.TruncateAt.END);
        top.addView(name, Toon.lp(0, -2, 1));
        android.widget.ImageView chevron = new android.widget.ImageView(this);
        chevron.setImageDrawable(new Icon(Icon.NEXT, Toon.MUTED, dp(24)));
        top.addView(chevron);
        box.addView(top);

        int total = l.size();
        String meta = total == 0 ? "Empty — tap to add pictures"
                : total + (total == 1 ? " picture" : " pictures")
                + (l.queue.isEmpty() ? " · all rated" : " · " + l.queue.size() + " to rate");
        TextView m = Toon.text(this, meta, 15, Toon.MUTED, false);
        m.setPadding(0, dp(4), 0, 0);
        box.addView(m);

        if (total > 0) {
            box.addView(new TierBar(this, l), Toon.margins(Toon.lp(-1, dp(14)), 0, dp(12), 0, 0));
            LinearLayout strip = Toon.row(this);
            ArrayList<TierList.Item> items = l.allItems();
            int size = dp(46);
            int shown = Math.min(items.size(), 6);
            for (int i = 0; i < shown; i++) {
                ThumbView t = new ThumbView(this, dp(9), dp(2.5f));
                Thumbs.into(t, Store.image(this, items.get(i).image), size);
                strip.addView(t, Toon.margins(Toon.lp(size, size), 0, 0, dp(7), 0));
            }
            if (items.size() > shown) {
                TextView more = Toon.text(this, "+" + (items.size() - shown), 15, Toon.MUTED, true);
                strip.addView(more);
            }
            box.addView(strip, Toon.margins(Toon.lp(-1, -2), 0, dp(12), 0, 0));
        }

        box.setClickable(true);
        Toon.pressSquish(box);
        box.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { open(l); }
        });
        box.setOnLongClickListener(new View.OnLongClickListener() {
            @Override public boolean onLongClick(View v) {
                options(l);
                return true;
            }
        });
        return box;
    }

    private void newList() {
        Toon.prompt(this, "New tier list", "", "e.g. Best snacks", "Create", new Toon.Text() {
            @Override public void on(String name) {
                open(Store.create(MainActivity.this, name.isEmpty() ? "My tier list" : name));
            }
        });
    }

    private void open(TierList l) {
        startActivity(new Intent(this, BoardActivity.class).putExtra(BoardActivity.EXTRA_ID, l.id));
    }

    private void options(final TierList l) {
        Toon.menu(this, l.name, new String[]{"Open", "Rename", "Delete"},
                new int[]{Toon.SUN, Toon.LILAC, Toon.CORAL}, new Toon.Pick() {
                    @Override public void on(int which) {
                        if (which == 0) open(l);
                        else if (which == 1) rename(l);
                        else delete(l);
                    }
                });
    }

    private void rename(final TierList l) {
        Toon.prompt(this, "Rename", l.name, "Name", "Save", new Toon.Text() {
            @Override public void on(String name) {
                if (name.isEmpty()) return;
                l.name = name;
                Store.save(MainActivity.this, l);
                render();
            }
        });
    }

    private void delete(final TierList l) {
        Toon.confirm(this, "Delete “" + l.name + "”?",
                "Its " + l.size() + " pictures will be removed from the app. This can’t be undone.",
                "Delete", new Runnable() {
                    @Override public void run() {
                        Store.delete(MainActivity.this, l);
                        render();
                    }
                });
    }

    /** A strip showing how the pictures split across the tiers, in tier colours. */
    private static final class TierBar extends View {
        private final TierList list;
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF rect = new RectF();

        TierBar(Context c, TierList list) {
            super(c);
            this.list = list;
        }

        @Override protected void onDraw(Canvas c) {
            float stroke = Toon.dp(getContext(), 2.5f);
            rect.set(stroke / 2, stroke / 2, getWidth() - stroke / 2, getHeight() - stroke / 2);
            float r = rect.height() / 2;
            int total = list.size();
            c.save();
            android.graphics.Path clip = new android.graphics.Path();
            clip.addRoundRect(rect, r, r, android.graphics.Path.Direction.CW);
            c.clipPath(clip);
            paint.setStyle(Paint.Style.FILL);
            paint.setColor(Toon.LILAC);
            c.drawRect(rect, paint);
            float x = rect.left;
            for (TierList.Tier t : list.tiers) {
                if (t.items.isEmpty()) continue;
                float w = rect.width() * t.items.size() / total;
                paint.setColor(t.color);
                c.drawRect(x, rect.top, x + w, rect.bottom, paint);
                paint.setColor(Toon.INK);
                paint.setStrokeWidth(stroke * 0.7f);
                c.drawLine(x + w, rect.top, x + w, rect.bottom, paint);
                x += w;
            }
            c.restore();
            paint.setStyle(Paint.Style.STROKE);
            paint.setStrokeWidth(stroke);
            paint.setColor(Toon.INK);
            c.drawRoundRect(rect, r, r, paint);
        }
    }
}
