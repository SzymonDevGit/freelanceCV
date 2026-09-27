package uk.co.cheltenhamdata.rately;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.graphics.BitmapFactory;
import android.os.Bundle;
import android.text.Editable;
import android.text.InputFilter;
import android.text.InputType;
import android.text.Spanned;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

/**
 * Puts text over a picture: type it, drag it into place, pick a size and a
 * colour. Returns the caption as JSON, or null when it was removed.
 */
public class CaptionActivity extends Activity {

    /** Absolute path of the square picture to preview. */
    static final String EXTRA_IMAGE = "image";
    /** The caption to start from, as JSON; absent for a new one. Also the result. */
    static final String EXTRA_CAPTION = "caption";
    /** Handed back untouched, so the caller knows which picture this was for. */
    static final String EXTRA_ITEM = "item";

    private Caption caption;
    private CaptionView preview;
    private EditText input;
    private LinearLayout sizes;
    private LinearLayout colors;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        String json = state != null ? state.getString(EXTRA_CAPTION) : getIntent().getStringExtra(EXTRA_CAPTION);
        caption = Caption.fromJson(json);
        boolean editing = caption != null && getIntent().getStringExtra(EXTRA_CAPTION) != null;
        if (caption == null) caption = new Caption();
        getWindow().setStatusBarColor(Toon.DUSK);
        getWindow().setNavigationBarColor(Toon.DUSK);
        setContentView(build(editing));
        input.requestFocus();
    }

    @Override protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        out.putString(EXTRA_CAPTION, caption.toJsonString());
    }

    private int dp(float v) {
        return Toon.dp(this, v);
    }

    private View build(boolean editing) {
        LinearLayout root = Toon.column(this);
        root.setBackgroundColor(Toon.DUSK);
        root.setPadding(dp(16), dp(12), dp(16), dp(16));

        LinearLayout bar = Toon.row(this);
        ImageView close = Toon.iconButton(this, Icon.CLOSE, Toon.CREAM, 46);
        close.setContentDescription("Cancel");
        close.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                setResult(RESULT_CANCELED);
                finish();
            }
        });
        bar.addView(close, Toon.lp(dp(48), dp(48)));
        TextView title = Toon.text(this, editing ? "Edit text" : "Add text", 22, Toon.CREAM, true);
        title.setPadding(dp(14), 0, 0, 0);
        bar.addView(title, Toon.lp(0, -2, 1));
        root.addView(bar);

        FrameLayout stage = new FrameLayout(this);
        RateActivity.SquareFrame square = new RateActivity.SquareFrame(this);
        preview = new CaptionView(this);
        preview.setImageBitmap(BitmapFactory.decodeFile(getIntent().getStringExtra(EXTRA_IMAGE)));
        preview.setCaption(caption);
        preview.setContentDescription("Picture preview. Drag the text to move it.");
        square.addView(preview, new FrameLayout.LayoutParams(-1, -1));
        stage.addView(square, new FrameLayout.LayoutParams(-2, -2, Gravity.CENTER));
        root.addView(stage, Toon.margins(Toon.lp(-1, 0, 1), 0, dp(12), 0, dp(6)));

        TextView hint = Toon.text(this, "Drag the text to move it", 15, Toon.LILAC, false);
        hint.setGravity(Gravity.CENTER);
        root.addView(hint, Toon.margins(Toon.lp(-1, -2), 0, 0, 0, dp(10)));

        input = Toon.input(this, caption.text, "Type something…");
        input.setSingleLine(false);
        input.setMaxLines(Caption.MAX_LINES);
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
                | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        input.setFilters(new InputFilter[]{new InputFilter.LengthFilter(60), new LineLimit()});
        input.setSelection(input.getText().length());
        input.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int st, int c, int af) {}
            @Override public void onTextChanged(CharSequence s, int st, int b, int c) {}
            @Override public void afterTextChanged(Editable s) {
                caption.text = s.toString();
                preview.invalidate();
            }
        });
        root.addView(input, Toon.lp(-1, -2));

        sizes = Toon.row(this);
        root.addView(sizes, Toon.margins(Toon.lp(-1, -2), 0, dp(12), 0, 0));
        colors = Toon.row(this);
        root.addView(colors, Toon.margins(Toon.lp(-1, -2), 0, dp(10), 0, 0));
        renderStyle();

        LinearLayout buttons = Toon.row(this);
        if (editing) {
            TextView remove = Toon.button(this, "Remove", Toon.CORAL);
            remove.setOnClickListener(new View.OnClickListener() {
                @Override public void onClick(View v) { finishWith(null); }
            });
            buttons.addView(remove, Toon.margins(Toon.lp(0, -2, 1), 0, 0, dp(10), 0));
        }
        TextView done = Toon.button(this, "", Toon.SUN);
        Toon.withIcon(this, done, Icon.CHECK, "Done");
        done.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { finishWith(caption.isEmpty() ? null : caption); }
        });
        buttons.addView(done, Toon.lp(0, -2, editing ? 1.4f : 1));
        root.addView(buttons, Toon.margins(Toon.lp(-1, -2), 0, dp(14), 0, 0));
        return root;
    }

    /** Rebuilds the size and colour pickers so the current choice is marked. */
    private void renderStyle() {
        sizes.removeAllViews();
        String[] names = {"Small", "Medium", "Large"};
        float[] textSp = {14, 17, 21};
        for (int i = 0; i < Caption.SIZES.length; i++) {
            final float s = Caption.SIZES[i];
            boolean on = Math.abs(caption.size - s) < 0.001f;
            TextView b = Toon.button(this, names[i], on ? Toon.SUN : Toon.LILAC);
            b.setTextSize(textSp[i]);
            b.setMinHeight(dp(48));
            b.setPadding(dp(4), dp(6), dp(8), dp(10));
            b.setOnClickListener(new View.OnClickListener() {
                @Override public void onClick(View v) {
                    caption.size = s;
                    preview.invalidate();
                    renderStyle();
                }
            });
            boolean last = i == Caption.SIZES.length - 1;
            sizes.addView(b, Toon.margins(Toon.lp(0, dp(48), 1), 0, 0, last ? 0 : dp(8), 0));
        }

        colors.removeAllViews();
        int n = Caption.COLORS.length;
        int gap = dp(6);
        int avail = getResources().getDisplayMetrics().widthPixels - dp(32);
        int size = Math.min(dp(46), (avail - gap * (n - 1)) / n);
        for (int i = 0; i < n; i++) {
            final int color = Caption.COLORS[i];
            ImageView s = Toon.iconButton(this, Icon.CHECK, color, 40);
            s.setImageDrawable(color == caption.color ? new Icon(Icon.CHECK, Toon.INK, dp(20)) : null);
            s.setContentDescription("Colour " + (i + 1));
            s.setOnClickListener(new View.OnClickListener() {
                @Override public void onClick(View v) {
                    caption.color = color;
                    preview.invalidate();
                    renderStyle();
                }
            });
            colors.addView(s, Toon.margins(Toon.lp(size, size), 0, 0, i == n - 1 ? 0 : gap, 0));
        }
    }

    private void finishWith(Caption c) {
        Intent data = new Intent().putExtra(EXTRA_ITEM, getIntent().getStringExtra(EXTRA_ITEM));
        if (c != null) data.putExtra(EXTRA_CAPTION, c.toJsonString());
        setResult(RESULT_OK, data);
        finish();
    }

    /** Stops the caption growing past Caption.MAX_LINES lines. */
    private static final class LineLimit implements InputFilter {
        @Override public CharSequence filter(CharSequence src, int start, int end, Spanned dest, int dstart, int dend) {
            int lines = 1;
            for (int i = 0; i < dest.length(); i++) {
                if ((i < dstart || i >= dend) && dest.charAt(i) == '\n') lines++;
            }
            StringBuilder out = new StringBuilder();
            for (int i = start; i < end; i++) {
                char ch = src.charAt(i);
                if (ch == '\n') {
                    if (lines >= Caption.MAX_LINES) continue;
                    lines++;
                }
                out.append(ch);
            }
            return out.length() == end - start ? null : out.toString();
        }
    }

    /** The preview: drag anywhere on it and the text follows your finger. */
    static final class CaptionView extends ThumbView {
        private float lastX;
        private float lastY;

        CaptionView(Context c) {
            super(c, Toon.dp(c, 18), Toon.dp(c, 3));
        }

        @Override public boolean onTouchEvent(MotionEvent e) {
            Caption cap = getCaption();
            if (cap == null || getWidth() == 0) return false;
            switch (e.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    lastX = e.getX();
                    lastY = e.getY();
                    getParent().requestDisallowInterceptTouchEvent(true);
                    return true;
                case MotionEvent.ACTION_MOVE:
                    cap.x = Math.max(0.05f, Math.min(0.95f, cap.x + (e.getX() - lastX) / getWidth()));
                    cap.y = Math.max(0.05f, Math.min(0.95f, cap.y + (e.getY() - lastY) / getHeight()));
                    lastX = e.getX();
                    lastY = e.getY();
                    invalidate();
                    return true;
                case MotionEvent.ACTION_UP:
                    performClick();
                    return true;
                default:
                    return true;
            }
        }

        @Override public boolean performClick() {
            return super.performClick();
        }
    }
}
