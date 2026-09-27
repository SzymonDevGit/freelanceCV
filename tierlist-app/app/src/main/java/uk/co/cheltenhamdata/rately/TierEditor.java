package uk.co.cheltenhamdata.rately;

import android.app.Activity;
import android.app.Dialog;
import android.content.DialogInterface;
import android.text.Editable;
import android.text.InputFilter;
import android.text.InputType;
import android.text.TextWatcher;
import android.view.View;
import android.view.WindowManager;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** Rename, recolour, reorder, add and remove the tiers of a list. */
final class TierEditor {

    private TierEditor() {}

    static void show(final Activity a, final TierList list, final Runnable changed) {
        LinearLayout box = Toon.column(a);
        box.addView(Toon.dialogTitle(a, "Edit tiers"));

        final int maxH = (int) (a.getResources().getDisplayMetrics().heightPixels * 0.5f);
        ScrollView scroll = new ScrollView(a) {
            @Override protected void onMeasure(int ws, int hs) {
                super.onMeasure(ws, MeasureSpec.makeMeasureSpec(maxH, MeasureSpec.AT_MOST));
            }
        };
        final LinearLayout rows = Toon.column(a);
        scroll.addView(rows);
        box.addView(scroll, Toon.lp(-1, -2));

        LinearLayout buttons = Toon.row(a);
        TextView add = Toon.button(a, "", Toon.LILAC);
        Toon.withIcon(a, add, Icon.PLUS, "Add tier");
        TextView done = Toon.button(a, "Done", Toon.SUN);
        buttons.addView(add, Toon.margins(Toon.lp(0, -2, 1), 0, 0, Toon.dp(a, 10), 0));
        buttons.addView(done, Toon.lp(0, -2, 1));
        box.addView(buttons, Toon.margins(Toon.lp(-1, -2), 0, Toon.dp(a, 14), 0, 0));

        final Dialog d = Toon.dialog(a, box);
        final Runnable[] refresh = new Runnable[1];
        refresh[0] = new Runnable() {
            @Override public void run() {
                rows.removeAllViews();
                for (int i = 0; i < list.tiers.size(); i++) {
                    rows.addView(row(a, list, list.tiers.get(i), i, refresh[0]),
                            Toon.margins(Toon.lp(-1, -2), 0, 0, 0, Toon.dp(a, 10)));
                }
            }
        };
        refresh[0].run();

        add.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                list.tiers.add(TierList.newTier(list.nextLabel(), list.nextColor()));
                refresh[0].run();
            }
        });
        done.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { d.dismiss(); }
        });
        d.setOnDismissListener(new DialogInterface.OnDismissListener() {
            @Override public void onDismiss(DialogInterface di) {
                Store.save(a, list);
                changed.run();
            }
        });
        d.getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        Toon.show(a, d);
    }

    private static View row(final Activity a, final TierList list, final TierList.Tier t, final int index,
                            final Runnable refresh) {
        LinearLayout row = Toon.row(a);
        int size = Toon.dp(a, 44);

        final TextView swatch = Toon.button(a, "", t.color);
        swatch.setMinHeight(0);
        swatch.setMinimumHeight(0);
        swatch.setPadding(0, 0, 0, 0);
        swatch.setContentDescription("Colour");
        swatch.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                palette(a, t, refresh);
            }
        });
        row.addView(swatch, Toon.margins(Toon.lp(size, size), 0, 0, Toon.dp(a, 8), 0));

        EditText label = Toon.input(a, t.label, "Label");
        label.setFilters(new InputFilter[]{new InputFilter.LengthFilter(16)});
        label.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_CHARACTERS);
        label.setPadding(Toon.dp(a, 12), Toon.dp(a, 8), Toon.dp(a, 12), Toon.dp(a, 8));
        label.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int st, int c, int af) {}
            @Override public void onTextChanged(CharSequence s, int st, int b, int c) {}
            @Override public void afterTextChanged(Editable s) { t.label = s.toString(); }
        });
        row.addView(label, Toon.margins(Toon.lp(0, size, 1), 0, 0, Toon.dp(a, 6), 0));

        int small = Toon.dp(a, 40);
        ImageView up = small(a, Icon.UP);
        up.setEnabled(index > 0);
        up.setContentDescription("Move up");
        up.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                list.tiers.remove(t);
                list.tiers.add(index - 1, t);
                refresh.run();
            }
        });
        row.addView(up, Toon.margins(Toon.lp(small, small), 0, 0, Toon.dp(a, 4), 0));

        ImageView down = small(a, Icon.DOWN);
        down.setEnabled(index < list.tiers.size() - 1);
        down.setContentDescription("Move down");
        down.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                list.tiers.remove(t);
                list.tiers.add(index + 1, t);
                refresh.run();
            }
        });
        row.addView(down, Toon.margins(Toon.lp(small, small), 0, 0, Toon.dp(a, 4), 0));

        ImageView remove = small(a, Icon.CLOSE);
        remove.setEnabled(list.tiers.size() > 1);
        remove.setContentDescription("Remove tier");
        remove.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                final int n = t.items.size();
                if (n == 0) {
                    list.removeTier(t);
                    refresh.run();
                    return;
                }
                Toon.confirm(a, "Remove tier “" + t.shownLabel() + "”?",
                        "Its " + n + (n == 1 ? " picture goes" : " pictures go") + " back to the to-rate pile.",
                        "Remove", new Runnable() {
                            @Override public void run() {
                                list.removeTier(t);
                                refresh.run();
                            }
                        });
            }
        });
        row.addView(remove, Toon.lp(small, small));
        return row;
    }

    private static ImageView small(Activity a, int icon) {
        ImageView b = Toon.iconButton(a, icon, Toon.CREAM, 40);
        b.setImageDrawable(new Icon(icon, Toon.INK, Toon.dp(a, 20)));
        return b;
    }

    private static void palette(Activity a, final TierList.Tier t, final Runnable refresh) {
        LinearLayout box = Toon.column(a);
        box.addView(Toon.dialogTitle(a, "Pick a colour"));
        final Dialog d = Toon.dialog(a, box);
        FlowLayout grid = new FlowLayout(a, Toon.dp(a, 10));
        int size = Toon.dp(a, 52);
        for (final int color : Toon.TIER_COLORS) {
            ImageView s = Toon.iconButton(a, Icon.CHECK, color, 52);
            if (color != t.color) s.setImageDrawable(null);
            s.setOnClickListener(new View.OnClickListener() {
                @Override public void onClick(View v) {
                    t.color = color;
                    d.dismiss();
                    refresh.run();
                }
            });
            grid.addView(s, new FlowLayout.LayoutParams(size, size));
        }
        box.addView(grid, Toon.lp(-1, -2));
        Toon.show(a, d);
    }
}
