package uk.co.cheltenhamdata.rately;

import android.animation.ObjectAnimator;
import android.animation.PropertyValuesHolder;
import android.animation.StateListAnimator;
import android.app.Activity;
import android.app.Dialog;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Typeface;
import android.graphics.drawable.ColorDrawable;
import android.graphics.drawable.StateListDrawable;
import android.text.InputFilter;
import android.text.InputType;
import android.text.SpannableStringBuilder;
import android.text.Spanned;
import android.text.style.ReplacementSpan;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.view.inputmethod.EditorInfo;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

/**
 * The cartoon look: a palette pulled from a moorland sunset, the Fredoka font,
 * chunky outlined shapes with hard offset shadows, and small dialog helpers.
 */
final class Toon {

    // Sky, from the top of the photo down to the horizon, then the hills.
    static final int INK = 0xFF2B2340;
    static final int NIGHT = 0xFF231C36;
    static final int DUSK = 0xFF3F3760;
    static final int PLUM = 0xFF514878;
    static final int MAUVE = 0xFF8C7AAE;
    static final int LILAC = 0xFFC7B8E6;
    static final int PEACH = 0xFFF4A259;
    static final int SUN = 0xFFFFD23F;
    static final int CREAM = 0xFFFFF4DE;
    static final int CORAL = 0xFFFF6B6B;
    static final int MUTED = 0xFF6B5E86;

    /** New lists use the first six (S to F); the tier editor offers them all. */
    static final int[] TIER_COLORS = {
            0xFFFF6B6B, 0xFFFF9F43, 0xFFFFD23F, 0xFF8BD17C, 0xFF5EC8D8, 0xFFB084F5,
            0xFFFF8FC7, 0xFF7A8BFF, 0xFFC9B79C, 0xFFA0E7E5, 0xFFF4F1EA, 0xFF9C8AAE,
    };

    private static Typeface bold;
    private static Typeface medium;

    private Toon() {}

    static Typeface bold(Context c) {
        if (bold == null) bold = Typeface.createFromAsset(c.getAssets(), "fonts/Fredoka-Bold.ttf");
        return bold;
    }

    static Typeface medium(Context c) {
        if (medium == null) medium = Typeface.createFromAsset(c.getAssets(), "fonts/Fredoka-Medium.ttf");
        return medium;
    }

    static int dp(Context c, float v) {
        return Math.round(v * c.getResources().getDisplayMetrics().density);
    }

    static int lighten(int color, float t) {
        return mix(color, Color.WHITE, t);
    }

    static int mix(int a, int b, float t) {
        int r = (int) (Color.red(a) + (Color.red(b) - Color.red(a)) * t);
        int g = (int) (Color.green(a) + (Color.green(b) - Color.green(a)) * t);
        int bl = (int) (Color.blue(a) + (Color.blue(b) - Color.blue(a)) * t);
        return Color.argb(Color.alpha(a), r, g, bl);
    }

    static TextView text(Context c, CharSequence s, float sp, int color, boolean isBold) {
        TextView t = new TextView(c);
        t.setText(s);
        t.setTextSize(TypedValue.COMPLEX_UNIT_SP, sp);
        t.setTextColor(color);
        t.setTypeface(isBold ? bold(c) : medium(c));
        t.setIncludeFontPadding(false);
        return t;
    }

    /** Text size for a tier label so "S" is huge and "Amazing" still fits. */
    static float labelSize(String label, float big) {
        int n = label.length();
        if (n <= 1) return big;
        if (n == 2) return big * 0.82f;
        if (n <= 4) return big * 0.62f;
        if (n <= 7) return big * 0.48f;
        return big * 0.4f;
    }

    /** A chunky rounded button with an outline and a hard shadow it sinks into when pressed. */
    static TextView button(Context c, CharSequence s, int fill) {
        TextView b = text(c, s, 18, INK, true);
        b.setGravity(Gravity.CENTER);
        b.setSingleLine(false);
        int shadow = dp(c, 4);
        b.setBackground(buttonBackground(c, fill, dp(c, 16), shadow));
        b.setPadding(dp(c, 16), dp(c, 12), dp(c, 16) + shadow, dp(c, 12) + shadow);
        b.setMinHeight(dp(c, 56));
        b.setClickable(true);
        b.setFocusable(true);
        pressShift(b, shadow);
        return b;
    }

    static ImageView iconButton(Context c, int icon, int fill, int sizeDp) {
        ImageView b = new ImageView(c);
        int shadow = dp(c, 3);
        b.setBackground(buttonBackground(c, fill, dp(c, sizeDp / 2f), shadow));
        b.setImageDrawable(new Icon(icon, INK, dp(c, 24)));
        b.setScaleType(ImageView.ScaleType.CENTER);
        b.setPadding(0, 0, shadow, shadow);
        b.setClickable(true);
        b.setFocusable(true);
        pressShift(b, shadow);
        return b;
    }

    /** Sets the text with an icon just before it, both centred together. */
    static void withIcon(Context c, TextView t, int icon, CharSequence text) {
        Icon i = new Icon(icon, t.getCurrentTextColor(), dp(c, 22));
        i.setBounds(0, 0, i.getIntrinsicWidth(), i.getIntrinsicHeight());
        SpannableStringBuilder s = new SpannableStringBuilder("\u00A0");
        s.setSpan(new IconSpan(i, dp(c, 8)), 0, 1, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        s.append(text);
        t.setText(s);
    }

    /** An inline icon, vertically centred on the text around it. */
    private static final class IconSpan extends ReplacementSpan {
        private final Icon icon;
        private final int gap;

        IconSpan(Icon icon, int gap) {
            this.icon = icon;
            this.gap = gap;
        }

        @Override public int getSize(Paint p, CharSequence text, int start, int end, Paint.FontMetricsInt fm) {
            return icon.getBounds().width() + gap;
        }

        @Override public void draw(Canvas c, CharSequence text, int start, int end, float x, int top, int y,
                                   int bottom, Paint p) {
            Paint.FontMetrics m = p.getFontMetrics();
            float center = y + (m.ascent + m.descent) / 2f;
            c.save();
            c.translate(x, center - icon.getBounds().height() / 2f);
            icon.draw(c);
            c.restore();
        }
    }

    static StateListDrawable buttonBackground(Context c, int fill, float radius, int shadow) {
        float stroke = dp(c, 3);
        ToonDrawable up = new ToonDrawable(fill, radius, shadow, stroke);
        up.shine = true;
        ToonDrawable down = new ToonDrawable(fill, radius, shadow, stroke);
        down.shadowVisible = false;
        ToonDrawable off = new ToonDrawable(mix(fill, MAUVE, 0.6f), radius, shadow, stroke);
        off.stroke = mix(INK, MAUVE, 0.35f);
        StateListDrawable s = new StateListDrawable();
        s.addState(new int[]{-android.R.attr.state_enabled}, off);
        s.addState(new int[]{android.R.attr.state_pressed}, down);
        s.addState(new int[0], up);
        return s;
    }

    /** Moves the view onto its own shadow while pressed. */
    static void pressShift(View v, float shadow) {
        StateListAnimator a = new StateListAnimator();
        a.addState(new int[]{android.R.attr.state_pressed, android.R.attr.state_enabled},
                ObjectAnimator.ofPropertyValuesHolder(v,
                        PropertyValuesHolder.ofFloat("translationX", shadow),
                        PropertyValuesHolder.ofFloat("translationY", shadow)).setDuration(40));
        a.addState(new int[0],
                ObjectAnimator.ofPropertyValuesHolder(v,
                        PropertyValuesHolder.ofFloat("translationX", 0),
                        PropertyValuesHolder.ofFloat("translationY", 0)).setDuration(90));
        v.setStateListAnimator(a);
    }

    /** Shrinks the view a little while pressed; for pictures and cards. */
    static void pressSquish(View v) {
        StateListAnimator a = new StateListAnimator();
        a.addState(new int[]{android.R.attr.state_pressed},
                ObjectAnimator.ofPropertyValuesHolder(v,
                        PropertyValuesHolder.ofFloat("scaleX", 0.94f),
                        PropertyValuesHolder.ofFloat("scaleY", 0.94f)).setDuration(70));
        a.addState(new int[0],
                ObjectAnimator.ofPropertyValuesHolder(v,
                        PropertyValuesHolder.ofFloat("scaleX", 1f),
                        PropertyValuesHolder.ofFloat("scaleY", 1f)).setDuration(120));
        v.setStateListAnimator(a);
    }

    static EditText input(Context c, String value, String hint) {
        EditText e = new EditText(c);
        e.setText(value);
        e.setHint(hint);
        e.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18);
        e.setTextColor(INK);
        e.setHintTextColor(0xFF9A8FB5);
        e.setTypeface(medium(c));
        e.setSingleLine(true);
        e.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        e.setFilters(new InputFilter[]{new InputFilter.LengthFilter(40)});
        e.setBackground(new ToonDrawable(Color.WHITE, dp(c, 12), 0, dp(c, 3)));
        e.setPadding(dp(c, 14), dp(c, 12), dp(c, 14), dp(c, 12));
        e.setSelection(e.getText().length());
        return e;
    }

    static LinearLayout.LayoutParams lp(int w, int h) {
        return new LinearLayout.LayoutParams(w, h);
    }

    static LinearLayout.LayoutParams lp(int w, int h, float weight) {
        return new LinearLayout.LayoutParams(w, h, weight);
    }

    static LinearLayout.LayoutParams margins(LinearLayout.LayoutParams p, int l, int t, int r, int b) {
        p.setMargins(l, t, r, b);
        return p;
    }

    static void toast(Context c, String msg) {
        Toast.makeText(c, msg, Toast.LENGTH_SHORT).show();
    }

    // ---- Dialogs -------------------------------------------------------------------------------

    interface Pick {
        void on(int which);
    }

    interface Text {
        void on(String value);
    }

    /** A dialog whose content sits on a cream cartoon card. */
    static Dialog dialog(Activity a, View content) {
        final Dialog d = new Dialog(a);
        d.requestWindowFeature(Window.FEATURE_NO_TITLE);
        int shadow = dp(a, 6);
        content.setBackground(new ToonDrawable(CREAM, dp(a, 24), shadow, dp(a, 3)));
        int pad = dp(a, 20);
        content.setPadding(pad, pad, pad + shadow, pad + shadow);
        FrameLayout wrap = new FrameLayout(a);
        wrap.addView(content, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        d.setContentView(wrap);
        Window w = d.getWindow();
        w.setBackgroundDrawable(new ColorDrawable(Color.TRANSPARENT));
        w.setDimAmount(0.65f);
        return d;
    }

    static void show(Activity a, Dialog d) {
        d.show();
        int width = Math.min(a.getResources().getDisplayMetrics().widthPixels - dp(a, 28), dp(a, 440));
        d.getWindow().setLayout(width, ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    static LinearLayout column(Context c) {
        LinearLayout l = new LinearLayout(c);
        l.setOrientation(LinearLayout.VERTICAL);
        return l;
    }

    static LinearLayout row(Context c) {
        LinearLayout l = new LinearLayout(c);
        l.setOrientation(LinearLayout.HORIZONTAL);
        l.setGravity(Gravity.CENTER_VERTICAL);
        return l;
    }

    static TextView dialogTitle(Context c, String s) {
        TextView t = text(c, s, 24, INK, true);
        t.setPadding(0, 0, 0, dp(c, 14));
        return t;
    }

    static void prompt(final Activity a, String title, String value, String hint, String ok, final Text done) {
        LinearLayout box = column(a);
        box.addView(dialogTitle(a, title));
        final EditText input = input(a, value, hint);
        input.setImeOptions(EditorInfo.IME_ACTION_DONE);
        box.addView(input, lp(-1, -2));
        LinearLayout buttons = row(a);
        TextView cancel = button(a, "Cancel", LILAC);
        TextView yes = button(a, ok, SUN);
        buttons.addView(cancel, margins(lp(0, -2, 1), 0, 0, dp(a, 10), 0));
        buttons.addView(yes, lp(0, -2, 1));
        box.addView(buttons, margins(lp(-1, -2), 0, dp(a, 18), 0, 0));

        final Dialog d = dialog(a, box);
        final Runnable submit = new Runnable() {
            @Override public void run() {
                d.dismiss();
                done.on(input.getText().toString().trim());
            }
        };
        cancel.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { d.dismiss(); }
        });
        yes.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { submit.run(); }
        });
        input.setOnEditorActionListener(new TextView.OnEditorActionListener() {
            @Override public boolean onEditorAction(TextView v, int actionId, android.view.KeyEvent e) {
                submit.run();
                return true;
            }
        });
        d.getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_VISIBLE
                | WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        show(a, d);
        input.requestFocus();
    }

    static void confirm(Activity a, String title, String message, String ok, final Runnable yes) {
        LinearLayout box = column(a);
        box.addView(dialogTitle(a, title));
        TextView msg = text(a, message, 17, MUTED, false);
        msg.setLineSpacing(0, 1.15f);
        box.addView(msg);
        LinearLayout buttons = row(a);
        TextView no = button(a, "Cancel", LILAC);
        TextView go = button(a, ok, CORAL);
        buttons.addView(no, margins(lp(0, -2, 1), 0, 0, dp(a, 10), 0));
        buttons.addView(go, lp(0, -2, 1));
        box.addView(buttons, margins(lp(-1, -2), 0, dp(a, 20), 0, 0));
        final Dialog d = dialog(a, box);
        no.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { d.dismiss(); }
        });
        go.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                d.dismiss();
                yes.run();
            }
        });
        show(a, d);
    }

    static void menu(Activity a, String title, String[] labels, int[] fills, final Pick pick) {
        LinearLayout box = column(a);
        TextView t = dialogTitle(a, title);
        t.setSingleLine(true);
        t.setEllipsize(android.text.TextUtils.TruncateAt.END);
        box.addView(t);
        final Dialog d = dialog(a, box);
        for (int i = 0; i < labels.length; i++) {
            final int which = i;
            TextView b = button(a, labels[i], fills[i]);
            b.setOnClickListener(new View.OnClickListener() {
                @Override public void onClick(View v) {
                    d.dismiss();
                    pick.on(which);
                }
            });
            box.addView(b, margins(lp(-1, -2), 0, i == 0 ? 0 : dp(a, 10), 0, 0));
        }
        show(a, d);
    }
}
