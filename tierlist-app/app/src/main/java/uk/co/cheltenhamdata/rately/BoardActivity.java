package uk.co.cheltenhamdata.rately;

import android.app.Activity;
import android.app.Dialog;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.Intent;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.MediaStore;
import android.text.TextUtils;
import android.view.DragEvent;
import android.view.Gravity;
import android.view.HapticFeedbackConstants;
import android.view.View;
import android.widget.HorizontalScrollView;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.ArrayList;

/**
 * One tier list: a row per tier, pictures you can drag between rows, and a
 * dock at the bottom with the pictures still to rate.
 */
public class BoardActivity extends Activity {

    static final String EXTRA_ID = "list";
    private static final int REQ_PICK = 1;
    private static final int REQ_CROP = 2;
    /** MediaStore.ACTION_PICK_IMAGES and its extra, API 33; the app compiles against 23. */
    private static final String ACTION_PICK_IMAGES = "android.provider.action.PICK_IMAGES";
    private static final String EXTRA_PICK_IMAGES_MAX = "android.provider.extra.PICK_IMAGES_MAX";

    private TierList list;
    private ScrollView scroll;
    private LinearLayout rows;
    private LinearLayout trayItems;
    private TextView title;
    private TextView trayCount;
    private TextView trayEmpty;
    private TextView rateButton;
    private ToonDrawable dockBg;
    private HorizontalScrollView trayScroll;
    private int thumb;
    private int labelW;
    private int edgeDir;

    private final Runnable edgeScroller = new Runnable() {
        @Override public void run() {
            if (edgeDir == 0) return;
            scroll.scrollBy(0, edgeDir * dp(10));
            scroll.postDelayed(this, 16);
        }
    };

    private final Runnable render = new Runnable() {
        @Override public void run() { render(); }
    };

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        list = Store.get(this, getIntent().getStringExtra(EXTRA_ID));
        if (list == null) {
            finish();
            return;
        }
        getWindow().setStatusBarColor(Toon.DUSK);
        getWindow().setNavigationBarColor(Toon.PLUM);

        int screenW = getResources().getDisplayMetrics().widthPixels;
        labelW = dp(68);
        // Screen minus: list padding 12+12, row padding 6+6+shadow 4, label, flow padding 6+6, 3 gaps of 6.
        thumb = (screenW - dp(24) - dp(16) - labelW - dp(12) - dp(18)) / 4;

        setContentView(build());
    }

    @Override protected void onResume() {
        super.onResume();
        list = Store.get(this, list.id);
        if (list == null) {
            finish();
            return;
        }
        render();
    }

    @Override protected void onPause() {
        super.onPause();
        if (list != null) Store.flush(this, list);
    }

    private int dp(float v) {
        return Toon.dp(this, v);
    }

    // ---- Layout ----------------------------------------------------------------------------------

    private View build() {
        LinearLayout root = Toon.column(this);
        root.setBackground(new GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM,
                new int[]{Toon.DUSK, 0xFF342D52, Toon.NIGHT}));

        LinearLayout bar = Toon.row(this);
        bar.setPadding(dp(12), dp(10), dp(12), dp(8));
        ImageView back = Toon.iconButton(this, Icon.BACK, Toon.CREAM, 46);
        back.setContentDescription("Back");
        back.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { finish(); }
        });
        bar.addView(back, Toon.lp(dp(48), dp(48)));
        title = Toon.text(this, "", 24, Toon.CREAM, true);
        title.setSingleLine(true);
        title.setEllipsize(TextUtils.TruncateAt.END);
        title.setShadowLayer(0.01f, 0, dp(2), Toon.INK);
        title.setPadding(dp(12), 0, dp(8), 0);
        title.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { rename(); }
        });
        bar.addView(title, Toon.lp(0, -2, 1));
        ImageView tiers = Toon.iconButton(this, Icon.EDIT, Toon.LILAC, 46);
        tiers.setContentDescription("Edit tiers");
        tiers.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { editTiers(); }
        });
        bar.addView(tiers, Toon.margins(Toon.lp(dp(48), dp(48)), 0, 0, dp(8), 0));
        ImageView more = Toon.iconButton(this, Icon.MORE, Toon.LILAC, 46);
        more.setContentDescription("More");
        more.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { menu(); }
        });
        bar.addView(more, Toon.lp(dp(48), dp(48)));
        root.addView(bar);

        scroll = new ScrollView(this);
        scroll.setClipToPadding(false);
        rows = Toon.column(this);
        rows.setPadding(dp(12), dp(6), dp(12), dp(20));
        rows.setOnDragListener(new View.OnDragListener() {
            @Override public boolean onDrag(View v, DragEvent e) {
                if (e.getAction() == DragEvent.ACTION_DRAG_LOCATION) edge(e.getY() + rows.getTop());
                if (e.getAction() == DragEvent.ACTION_DRAG_ENDED) dragEnded();
                return true;
            }
        });
        scroll.addView(rows);
        root.addView(scroll, Toon.lp(-1, 0, 1));

        root.addView(buildDock(), Toon.margins(Toon.lp(-1, -2), -dp(4), 0, -dp(4), -dp(30)));
        return root;
    }

    private View buildDock() {
        LinearLayout dock = Toon.column(this);
        dockBg = new ToonDrawable(Toon.PLUM, dp(26), 0, dp(3));
        dock.setBackground(dockBg);
        dock.setPadding(dp(18), dp(14), dp(18), dp(44));

        LinearLayout head = Toon.row(this);
        TextView label = Toon.text(this, "TO RATE", 14, Toon.LILAC, true);
        label.setLetterSpacing(0.12f);
        head.addView(label);
        trayCount = Toon.text(this, "0", 14, Toon.INK, true);
        trayCount.setGravity(Gravity.CENTER);
        trayCount.setBackground(new ToonDrawable(Toon.SUN, dp(12), 0, dp(2)));
        trayCount.setPadding(dp(9), dp(3), dp(9), dp(3));
        head.addView(trayCount, Toon.margins(Toon.lp(-2, -2), dp(8), 0, 0, 0));
        dock.addView(head);

        trayScroll = new HorizontalScrollView(this);
        trayScroll.setHorizontalScrollBarEnabled(false);
        trayItems = Toon.row(this);
        trayItems.setPadding(0, dp(10), 0, dp(12));
        trayScroll.addView(trayItems);
        dock.addView(trayScroll, Toon.lp(-1, dp(80)));
        trayEmpty = Toon.text(this, "Nothing waiting. Add pictures to rate them.", 15, Toon.LILAC, false);
        trayEmpty.setGravity(Gravity.CENTER_VERTICAL);
        dock.addView(trayEmpty, Toon.lp(-1, dp(80)));

        LinearLayout buttons = Toon.row(this);
        TextView add = Toon.button(this, "", Toon.LILAC);
        Toon.withIcon(this, add, Icon.PLUS, "Add");
        add.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { pick(); }
        });
        buttons.addView(add, Toon.margins(Toon.lp(0, -2, 1), 0, 0, dp(12), 0));
        rateButton = Toon.button(this, "", Toon.SUN);
        rateButton.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { rate(); }
        });
        buttons.addView(rateButton, Toon.lp(0, -2, 1.4f));
        dock.addView(buttons);

        dock.setOnDragListener(new View.OnDragListener() {
            @Override public boolean onDrag(View v, DragEvent e) {
                switch (e.getAction()) {
                    case DragEvent.ACTION_DRAG_ENTERED:
                        edgeDir = 0;
                        dockBg.setHighlight(true);
                        break;
                    case DragEvent.ACTION_DRAG_EXITED:
                        dockBg.setHighlight(false);
                        break;
                    case DragEvent.ACTION_DROP:
                        dockBg.setHighlight(false);
                        TierList.Item it = list.findItem(String.valueOf(e.getLocalState()));
                        if (it != null && list.tierOf(it) != null) {
                            list.move(it, null, list.queue.size());
                            Store.save(BoardActivity.this, list);
                        }
                        rows.post(render);
                        break;
                    case DragEvent.ACTION_DRAG_ENDED:
                        dockBg.setHighlight(false);
                        break;
                    default:
                        break;
                }
                return true;
            }
        });
        return dock;
    }

    private void render() {
        title.setText(list.name);
        rows.removeAllViews();
        for (TierList.Tier t : list.tiers) {
            rows.addView(row(t), Toon.margins(Toon.lp(-1, -2), 0, 0, 0, dp(10)));
        }

        trayItems.removeAllViews();
        int size = dp(58);
        for (TierList.Item it : list.queue) {
            trayItems.addView(thumbFor(it, size), Toon.margins(Toon.lp(size, size), 0, 0, dp(8), 0));
        }
        boolean empty = list.queue.isEmpty();
        trayScroll.setVisibility(empty ? View.GONE : View.VISIBLE);
        trayEmpty.setVisibility(empty ? View.VISIBLE : View.GONE);
        trayCount.setText(String.valueOf(list.queue.size()));
        rateButton.setEnabled(!empty);
        Toon.withIcon(this, rateButton, Icon.STAR, empty ? "All rated" : "Rate " + list.queue.size());
    }

    private View row(final TierList.Tier t) {
        final LinearLayout row = Toon.row(this);
        row.setGravity(Gravity.TOP);
        int shadow = dp(4);
        final ToonDrawable bg = new ToonDrawable(Toon.PLUM, dp(16), shadow, dp(3));
        row.setBackground(bg);
        row.setPadding(dp(6), dp(6), dp(6) + shadow, dp(6) + shadow);

        String shown = t.shownLabel();
        TextView label = Toon.text(this, shown, Toon.labelSize(shown, 34), Toon.INK, true);
        label.setGravity(Gravity.CENTER);
        label.setMaxLines(3);
        label.setEllipsize(TextUtils.TruncateAt.END);
        label.setPadding(dp(4), dp(4), dp(4), dp(4));
        label.setBackground(new ToonDrawable(t.color, dp(12), 0, dp(3)));
        label.setMinHeight(thumb + dp(12));
        label.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { editTiers(); }
        });
        row.addView(label, Toon.lp(labelW, -1));

        final FlowLayout flow = new FlowLayout(this, dp(6));
        flow.setPadding(dp(6), dp(6), dp(6), dp(6));
        flow.setMinimumHeight(thumb + dp(12));
        for (TierList.Item it : t.items) flow.addView(thumbFor(it, thumb), new FlowLayout.LayoutParams(thumb, thumb));
        row.addView(flow, Toon.lp(0, -2, 1));

        row.setOnDragListener(new View.OnDragListener() {
            @Override public boolean onDrag(View v, DragEvent e) {
                float fx = e.getX() - flow.getLeft();
                float fy = e.getY() - flow.getTop();
                switch (e.getAction()) {
                    case DragEvent.ACTION_DRAG_ENTERED:
                        bg.setHighlight(true);
                        break;
                    case DragEvent.ACTION_DRAG_LOCATION:
                        flow.setDropIndex(flow.indexAt(fx, fy));
                        edge(rows.getTop() + row.getTop() + e.getY());
                        break;
                    case DragEvent.ACTION_DRAG_EXITED:
                        bg.setHighlight(false);
                        flow.setDropIndex(-1);
                        break;
                    case DragEvent.ACTION_DROP:
                        bg.setHighlight(false);
                        flow.setDropIndex(-1);
                        TierList.Item it = list.findItem(String.valueOf(e.getLocalState()));
                        if (it != null) {
                            list.move(it, t, flow.indexAt(fx, fy));
                            Store.save(BoardActivity.this, list);
                        }
                        rows.post(render);
                        break;
                    case DragEvent.ACTION_DRAG_ENDED:
                        bg.setHighlight(false);
                        flow.setDropIndex(-1);
                        break;
                    default:
                        break;
                }
                return true;
            }
        });
        return row;
    }

    private View thumbFor(final TierList.Item it, int size) {
        final ThumbView v = new ThumbView(this, dp(10), dp(2.5f));
        Thumbs.into(v, Store.image(this, it.image), size);
        v.setClickable(true);
        Toon.pressSquish(v);
        v.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View view) { showItem(it); }
        });
        v.setOnLongClickListener(new View.OnLongClickListener() {
            @Override public boolean onLongClick(View view) {
                view.startDrag(ClipData.newPlainText("rately", it.id), new View.DragShadowBuilder(view), it.id, 0);
                view.setAlpha(0.3f);
                view.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS);
                return true;
            }
        });
        return v;
    }

    /** Scrolls the board while a drag hovers near its top or bottom edge; y is in scroll content. */
    private void edge(float contentY) {
        float y = contentY - scroll.getScrollY();
        int zone = dp(70);
        int dir = y < zone ? -1 : y > scroll.getHeight() - zone ? 1 : 0;
        if (dir != 0 && edgeDir == 0) {
            edgeDir = dir;
            scroll.post(edgeScroller);
        }
        edgeDir = dir;
    }

    private void dragEnded() {
        edgeDir = 0;
        rows.post(render);
    }

    // ---- Actions ---------------------------------------------------------------------------------

    private void showItem(final TierList.Item it) {
        LinearLayout box = Toon.column(this);
        int dialogW = Math.min(getResources().getDisplayMetrics().widthPixels - dp(28), dp(440));
        int side = Math.min(dialogW - dp(46), (int) (getResources().getDisplayMetrics().heightPixels * 0.42f));
        ThumbView big = new ThumbView(this, dp(16), dp(3));
        Thumbs.into(big, Store.image(this, it.image), side);
        LinearLayout.LayoutParams bigLp = Toon.lp(side, side);
        bigLp.gravity = Gravity.CENTER_HORIZONTAL;
        box.addView(big, bigLp);

        TextView move = Toon.text(this, "Move to", 16, Toon.MUTED, true);
        move.setPadding(0, dp(14), 0, dp(8));
        box.addView(move);

        final Dialog d = Toon.dialog(this, box);
        FlowLayout tiers = new FlowLayout(this, dp(8));
        TierList.Tier current = list.tierOf(it);
        for (final TierList.Tier t : list.tiers) {
            TextView b = Toon.button(this, t.shownLabel(), t.color);
            b.setMinWidth(dp(58));
            b.setMinHeight(dp(52));
            b.setPadding(dp(10), dp(8), dp(14), dp(12));
            b.setMaxLines(1);
            b.setEnabled(t != current);
            b.setOnClickListener(new View.OnClickListener() {
                @Override public void onClick(View v) {
                    list.move(it, t, t.items.size());
                    Store.save(BoardActivity.this, list);
                    d.dismiss();
                    render();
                }
            });
            tiers.addView(b, new FlowLayout.LayoutParams(-2, -2));
        }
        box.addView(tiers, Toon.lp(-1, -2));

        LinearLayout actions = Toon.row(this);
        TextView unrate = Toon.button(this, "To rate", Toon.LILAC);
        unrate.setEnabled(current != null);
        unrate.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                list.move(it, null, 0);
                Store.save(BoardActivity.this, list);
                d.dismiss();
                render();
            }
        });
        actions.addView(unrate, Toon.margins(Toon.lp(0, -2, 1), 0, 0, dp(10), 0));
        TextView delete = Toon.button(this, "Delete", Toon.CORAL);
        delete.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                d.dismiss();
                list.remove(it);
                Store.deleteImage(BoardActivity.this, it);
                Store.save(BoardActivity.this, list);
                render();
            }
        });
        actions.addView(delete, Toon.lp(0, -2, 1));
        box.addView(actions, Toon.margins(Toon.lp(-1, -2), 0, dp(16), 0, 0));
        Toon.show(this, d);
    }

    private void rename() {
        Toon.prompt(this, "Rename", list.name, "Name", "Save", new Toon.Text() {
            @Override public void on(String name) {
                if (name.isEmpty()) return;
                list.name = name;
                Store.save(BoardActivity.this, list);
                render();
            }
        });
    }

    private void editTiers() {
        TierEditor.show(this, list, render);
    }

    private void menu() {
        Toon.menu(this, list.name,
                new String[]{"Rename list", "Edit tiers", "Re-rate everything", "Delete list"},
                new int[]{Toon.LILAC, Toon.LILAC, Toon.SUN, Toon.CORAL}, new Toon.Pick() {
                    @Override public void on(int which) {
                        switch (which) {
                            case 0: rename(); break;
                            case 1: editTiers(); break;
                            case 2: rerateAll(); break;
                            default: deleteList(); break;
                        }
                    }
                });
    }

    private void rerateAll() {
        if (list.queue.size() == list.size()) {
            Toon.toast(this, "Everything is already waiting to be rated");
            return;
        }
        list.unrateAll();
        Store.save(this, list);
        render();
        rate();
    }

    private void deleteList() {
        Toon.confirm(this, "Delete “" + list.name + "”?",
                "Its " + list.size() + " pictures will be removed from the app. This can’t be undone.",
                "Delete", new Runnable() {
                    @Override public void run() {
                        Store.delete(BoardActivity.this, list);
                        list = null;
                        finish();
                    }
                });
    }

    private void rate() {
        if (list.queue.isEmpty()) return;
        startActivity(new Intent(this, RateActivity.class).putExtra(RateActivity.EXTRA_ID, list.id));
    }

    private void pick() {
        if (Build.VERSION.SDK_INT >= 33) {
            Intent i = new Intent(ACTION_PICK_IMAGES);
            i.setType("image/*");
            i.putExtra(EXTRA_PICK_IMAGES_MAX, pickLimit());
            try {
                startActivityForResult(i, REQ_PICK);
                return;
            } catch (ActivityNotFoundException e) {
                // Fall through to the document picker.
            }
        }
        Intent i = new Intent(Intent.ACTION_GET_CONTENT);
        i.setType("image/*");
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
        try {
            startActivityForResult(Intent.createChooser(i, "Add pictures"), REQ_PICK);
        } catch (ActivityNotFoundException e) {
            Toon.toast(this, "No app on this phone can pick pictures");
        }
    }

    private static int pickLimit() {
        try {
            return (Integer) MediaStore.class.getMethod("getPickImagesMaxLimit").invoke(null);
        } catch (Exception e) {
            return 50;
        }
    }

    @Override protected void onActivityResult(int req, int result, Intent data) {
        super.onActivityResult(req, result, data);
        if (list == null || result != RESULT_OK || data == null) return;
        if (req == REQ_PICK) {
            ArrayList<Uri> uris = new ArrayList<>();
            ClipData clip = data.getClipData();
            if (clip != null) {
                for (int i = 0; i < clip.getItemCount(); i++) {
                    Uri u = clip.getItemAt(i).getUri();
                    if (u != null) uris.add(u);
                }
            } else if (data.getData() != null) {
                uris.add(data.getData());
            }
            if (uris.isEmpty()) return;
            Intent crop = new Intent(this, CropActivity.class)
                    .putExtra(CropActivity.EXTRA_ID, list.id)
                    .putParcelableArrayListExtra(CropActivity.EXTRA_URIS, uris)
                    .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            // Carry the read grants for every picked picture over to the crop screen.
            ClipData grants = ClipData.newRawUri("pictures", uris.get(0));
            for (int i = 1; i < uris.size(); i++) grants.addItem(new ClipData.Item(uris.get(i)));
            crop.setClipData(grants);
            startActivityForResult(crop, REQ_CROP);
        } else if (req == REQ_CROP) {
            if (data.getIntExtra(CropActivity.RESULT_ADDED, 0) > 0) rate();
        }
    }
}
