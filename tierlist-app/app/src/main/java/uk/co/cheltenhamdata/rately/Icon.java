package uk.co.cheltenhamdata.rately;

import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.drawable.Drawable;

/** Round-capped line icons drawn on a 24-unit grid, so they match the chunky outlines. */
final class Icon extends Drawable {

    static final int BACK = 0;
    static final int CLOSE = 1;
    static final int UNDO = 2;
    static final int PLUS = 3;
    static final int STAR = 4;
    static final int MORE = 5;
    static final int ROTATE = 6;
    static final int CHECK = 7;
    static final int NEXT = 8;
    static final int EDIT = 9;
    static final int UP = 10;
    static final int DOWN = 11;
    static final int TEXT = 12;

    private final int type;
    private final int size;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path path = new Path();

    Icon(int type, int color, int sizePx) {
        this.type = type;
        this.size = sizePx;
        paint.setColor(color);
        paint.setStrokeCap(Paint.Cap.ROUND);
        paint.setStrokeJoin(Paint.Join.ROUND);
        build();
    }

    private void build() {
        Path p = path;
        switch (type) {
            case BACK:
                p.moveTo(15, 5); p.lineTo(8, 12); p.lineTo(15, 19);
                break;
            case NEXT:
                p.moveTo(9, 5); p.lineTo(16, 12); p.lineTo(9, 19);
                break;
            case UP:
                p.moveTo(5, 15); p.lineTo(12, 8); p.lineTo(19, 15);
                break;
            case DOWN:
                p.moveTo(5, 9); p.lineTo(12, 16); p.lineTo(19, 9);
                break;
            case TEXT:
                p.moveTo(5.5f, 7.5f); p.lineTo(5.5f, 5.5f); p.lineTo(18.5f, 5.5f); p.lineTo(18.5f, 7.5f);
                p.moveTo(12, 5.5f); p.lineTo(12, 18.5f);
                p.moveTo(9.5f, 18.5f); p.lineTo(14.5f, 18.5f);
                break;
            case CLOSE:
                p.moveTo(6, 6); p.lineTo(18, 18); p.moveTo(18, 6); p.lineTo(6, 18);
                break;
            case PLUS:
                p.moveTo(12, 5); p.lineTo(12, 19); p.moveTo(5, 12); p.lineTo(19, 12);
                break;
            case CHECK:
                p.moveTo(5, 12.5f); p.lineTo(10, 17.5f); p.lineTo(19, 7);
                break;
            case UNDO:
                p.moveTo(8.5f, 5.5f); p.lineTo(4.5f, 9.5f); p.lineTo(8.5f, 13.5f);
                p.moveTo(4.5f, 9.5f); p.lineTo(13.5f, 9.5f);
                p.arcTo(new RectF(8.5f, 9.5f, 18.5f, 19.5f), -90, 180);
                p.lineTo(9, 19.5f);
                break;
            case ROTATE: {
                // Clockwise arc ending top right, with the arrowhead pointing along it.
                RectF o = new RectF(5, 5.5f, 19, 19.5f);
                p.addArc(o, 35, 280);
                double end = Math.toRadians(315);
                float ex = (float) (12 + 7 * Math.cos(end));
                float ey = (float) (12.5f + 7 * Math.sin(end));
                double back = end - Math.PI / 2;
                double w1 = back - Math.toRadians(40);
                double w2 = back + Math.toRadians(40);
                p.moveTo(ex + 4.5f * (float) Math.cos(w1), ey + 4.5f * (float) Math.sin(w1));
                p.lineTo(ex, ey);
                p.lineTo(ex + 4.5f * (float) Math.cos(w2), ey + 4.5f * (float) Math.sin(w2));
                break;
            }
            case EDIT:
                p.moveTo(5, 19); p.lineTo(6, 14.5f); p.lineTo(15.5f, 5); p.lineTo(19, 8.5f);
                p.lineTo(9.5f, 18); p.close();
                p.moveTo(13, 7.5f); p.lineTo(16.5f, 11);
                break;
            case STAR:
                for (int i = 0; i < 10; i++) {
                    double a = Math.toRadians(-90 + i * 36);
                    float r = (i % 2 == 0) ? 8.5f : 3.9f;
                    float x = (float) (12 + r * Math.cos(a));
                    float y = (float) (12.8f + r * Math.sin(a));
                    if (i == 0) p.moveTo(x, y); else p.lineTo(x, y);
                }
                p.close();
                break;
            case MORE:
                p.addCircle(5.5f, 12, 2.3f, Path.Direction.CW);
                p.addCircle(12, 12, 2.3f, Path.Direction.CW);
                p.addCircle(18.5f, 12, 2.3f, Path.Direction.CW);
                break;
            default:
                break;
        }
    }

    @Override public void draw(Canvas c) {
        Rect b = getBounds();
        float s = Math.min(b.width(), b.height()) / 24f;
        c.save();
        c.translate(b.centerX() - 12 * s, b.centerY() - 12 * s);
        c.scale(s, s);
        if (type == STAR || type == MORE) {
            paint.setStyle(Paint.Style.FILL_AND_STROKE);
            paint.setStrokeWidth(1.6f);
        } else {
            paint.setStyle(Paint.Style.STROKE);
            paint.setStrokeWidth(3f);
        }
        c.drawPath(path, paint);
        c.restore();
    }

    @Override public int getIntrinsicWidth() {
        return size;
    }

    @Override public int getIntrinsicHeight() {
        return size;
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
