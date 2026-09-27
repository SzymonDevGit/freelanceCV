package uk.co.cheltenhamdata.rately;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.util.TypedValue;
import android.view.View;

/** One line of big title text with a thick ink outline and a hard drop shadow. */
final class ToonText extends View {

    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private String text;
    private int fill;
    private final float outline;
    private final float drop;
    private boolean centered;

    ToonText(Context c, String text, float sp, int fill) {
        super(c);
        this.text = text;
        this.fill = fill;
        paint.setTypeface(Toon.bold(c));
        paint.setTextSize(TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, sp,
                c.getResources().getDisplayMetrics()));
        paint.setStrokeJoin(Paint.Join.ROUND);
        outline = Math.max(Toon.dp(c, 2), paint.getTextSize() * 0.075f);
        drop = outline * 0.9f;
    }

    void setText(String t) {
        text = t;
        requestLayout();
        invalidate();
    }

    void setCentered(boolean c) {
        centered = c;
        invalidate();
    }

    @Override protected void onMeasure(int ws, int hs) {
        Paint.FontMetrics fm = paint.getFontMetrics();
        int w = (int) Math.ceil(paint.measureText(text) + outline * 2 + drop);
        int h = (int) Math.ceil(fm.descent - fm.ascent + outline * 2 + drop);
        setMeasuredDimension(resolveSize(w, ws), resolveSize(h, hs));
    }

    @Override protected void onDraw(Canvas c) {
        Paint.FontMetrics fm = paint.getFontMetrics();
        float textW = paint.measureText(text);
        float x = centered ? (getWidth() - drop - textW) / 2f : outline;
        float y = outline - fm.ascent;

        paint.setStyle(Paint.Style.FILL_AND_STROKE);
        paint.setStrokeWidth(outline * 2);
        paint.setColor(Toon.INK);
        c.drawText(text, x + drop, y + drop, paint);
        c.drawText(text, x, y, paint);

        paint.setStyle(Paint.Style.FILL);
        paint.setColor(fill);
        c.drawText(text, x, y, paint);
    }
}
