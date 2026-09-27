package uk.co.cheltenhamdata.rately;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.widget.ImageView;

/** A square picture with rounded corners, an ink outline and, optionally, its caption. */
class ThumbView extends ImageView {

    private final Path clip = new Path();
    private final RectF rect = new RectF();
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint captionPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final float radius;
    private final float stroke;
    private Caption caption;

    ThumbView(Context c, float radiusPx, float strokePx) {
        super(c);
        radius = radiusPx;
        stroke = strokePx;
        setScaleType(ScaleType.CENTER_CROP);
    }

    void setCaption(Caption c) {
        caption = c;
        invalidate();
    }

    Caption getCaption() {
        return caption;
    }

    @Override protected void onSizeChanged(int w, int h, int ow, int oh) {
        super.onSizeChanged(w, h, ow, oh);
        rect.set(stroke / 2, stroke / 2, w - stroke / 2, h - stroke / 2);
        clip.reset();
        clip.addRoundRect(rect, radius, radius, Path.Direction.CW);
    }

    @Override protected void onDraw(Canvas c) {
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(Toon.MAUVE);
        c.drawRoundRect(rect, radius, radius, paint);
        c.save();
        c.clipPath(clip);
        super.onDraw(c);
        if (caption != null) {
            caption.draw(c, captionPaint, Toon.bold(getContext()), 0, 0, Math.min(getWidth(), getHeight()));
        }
        c.restore();
        if (stroke > 0) {
            paint.setStyle(Paint.Style.STROKE);
            paint.setStrokeWidth(stroke);
            paint.setColor(Toon.INK);
            c.drawRoundRect(rect, radius, radius, paint);
        }
    }
}
