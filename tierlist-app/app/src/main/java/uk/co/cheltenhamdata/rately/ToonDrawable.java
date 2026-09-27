package uk.co.cheltenhamdata.rately;

import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.drawable.Drawable;

/**
 * A flat rounded shape with a thick ink outline and a hard shadow offset to the
 * bottom right. The shadow sits inside the bounds, so views give it extra
 * padding on those two sides.
 */
final class ToonDrawable extends Drawable {

    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF rect = new RectF();

    int fill;
    int stroke = Toon.INK;
    float strokeWidth;
    float radius;
    float shadow;
    boolean shadowVisible = true;
    /** A short white gleam along the top edge. */
    boolean shine;
    /** Drop-target state: lighter fill, sun-yellow outline. */
    private boolean highlight;

    ToonDrawable(int fill, float radius, float shadow, float strokeWidth) {
        this.fill = fill;
        this.radius = radius;
        this.shadow = shadow;
        this.strokeWidth = strokeWidth;
        paint.setStrokeCap(Paint.Cap.ROUND);
        paint.setStrokeJoin(Paint.Join.ROUND);
    }

    void setHighlight(boolean on) {
        if (highlight != on) {
            highlight = on;
            invalidateSelf();
        }
    }

    void setFill(int color) {
        fill = color;
        invalidateSelf();
    }

    @Override public void draw(Canvas c) {
        Rect b = getBounds();
        float h = strokeWidth / 2f;
        rect.set(b.left + h, b.top + h, b.right - h - shadow, b.bottom - h - shadow);
        float r = Math.min(radius, Math.min(rect.width(), rect.height()) / 2f);

        if (shadow > 0 && shadowVisible) {
            paint.setStyle(Paint.Style.FILL);
            paint.setColor(Toon.INK);
            rect.offset(shadow, shadow);
            c.drawRoundRect(rect, r, r, paint);
            rect.offset(-shadow, -shadow);
        }

        paint.setStyle(Paint.Style.FILL);
        paint.setColor(highlight ? Toon.lighten(fill, 0.22f) : fill);
        c.drawRoundRect(rect, r, r, paint);

        if (shine && rect.width() > r * 3) {
            paint.setStyle(Paint.Style.STROKE);
            paint.setStrokeWidth(Math.max(2f, strokeWidth * 0.9f));
            paint.setColor(0x73FFFFFF);
            float y = rect.top + strokeWidth * 1.7f;
            float x0 = rect.left + r * 0.9f;
            c.drawLine(x0, y, x0 + Math.min(rect.width() * 0.28f, strokeWidth * 12), y, paint);
        }

        if (strokeWidth > 0) {
            paint.setStyle(Paint.Style.STROKE);
            paint.setStrokeWidth(highlight ? strokeWidth * 1.4f : strokeWidth);
            paint.setColor(highlight ? Toon.SUN : stroke);
            c.drawRoundRect(rect, r, r, paint);
        }
    }

    @Override public void setAlpha(int alpha) {
        paint.setAlpha(alpha);
    }

    @Override public void setColorFilter(ColorFilter cf) {
        paint.setColorFilter(cf);
    }

    @Override public int getOpacity() {
        return PixelFormat.TRANSLUCENT;
    }
}
