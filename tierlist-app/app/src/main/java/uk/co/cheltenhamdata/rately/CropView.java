package uk.co.cheltenhamdata.rately;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.view.GestureDetector;
import android.view.MotionEvent;
import android.view.ScaleGestureDetector;
import android.view.View;

/**
 * Shows a photo under a fixed square frame. Pinch to zoom, drag to move; the
 * photo always covers the frame, so every crop is a full 1:1 square.
 */
final class CropView extends View {

    private static final float MAX_ZOOM = 8f;

    private Bitmap bitmap;
    private final Matrix matrix = new Matrix();
    private final RectF frame = new RectF();
    private final RectF tmp = new RectF();
    private final float[] values = new float[9];
    private final Path shade = new Path();
    private final Paint bmpPaint = new Paint(Paint.FILTER_BITMAP_FLAG | Paint.ANTI_ALIAS_FLAG);
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint captionPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final ScaleGestureDetector scaler;
    private final GestureDetector gestures;
    private final float radius;
    private float minScale = 1;
    private boolean touching;
    private String message = "Loading…";
    private Caption caption;

    CropView(Context c) {
        super(c);
        radius = Toon.dp(c, 18);
        paint.setStrokeCap(Paint.Cap.ROUND);
        paint.setStrokeJoin(Paint.Join.ROUND);
        paint.setTypeface(Toon.bold(c));
        paint.setTextAlign(Paint.Align.CENTER);
        scaler = new ScaleGestureDetector(c, new ScaleGestureDetector.SimpleOnScaleGestureListener() {
            @Override public boolean onScale(ScaleGestureDetector d) {
                if (bitmap == null) return false;
                float cur = scale();
                float next = Math.max(minScale, Math.min(minScale * MAX_ZOOM, cur * d.getScaleFactor()));
                matrix.postScale(next / cur, next / cur, d.getFocusX(), d.getFocusY());
                keepCovered();
                invalidate();
                return true;
            }
        });
        gestures = new GestureDetector(c, new GestureDetector.SimpleOnGestureListener() {
            @Override public boolean onDown(MotionEvent e) {
                return true;
            }

            @Override public boolean onScroll(MotionEvent e1, MotionEvent e2, float dx, float dy) {
                if (bitmap == null) return false;
                matrix.postTranslate(-dx, -dy);
                keepCovered();
                invalidate();
                return true;
            }

            @Override public boolean onDoubleTap(MotionEvent e) {
                if (bitmap == null) return false;
                if (scale() > minScale * 1.05f) {
                    fit();
                } else {
                    matrix.postScale(2.2f, 2.2f, e.getX(), e.getY());
                    keepCovered();
                }
                invalidate();
                return true;
            }
        });
    }

    void setBitmap(Bitmap b) {
        bitmap = b;
        fit();
        invalidate();
    }

    Bitmap getBitmap() {
        return bitmap;
    }

    /** Text shown over the framed square; it stays put while the photo moves. */
    void setCaption(Caption c) {
        caption = c;
        invalidate();
    }

    void setMessage(String m) {
        message = m;
        invalidate();
    }

    void rotate() {
        if (bitmap == null) return;
        bitmap = Images.rotate90(bitmap);
        fit();
        invalidate();
    }

    /** The framed square, as a size x size bitmap. */
    Bitmap crop(int size) {
        Bitmap out = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(out);
        c.drawColor(Color.WHITE);
        Matrix m = new Matrix(matrix);
        m.postTranslate(-frame.left, -frame.top);
        m.postScale(size / frame.width(), size / frame.width());
        c.drawBitmap(bitmap, m, bmpPaint);
        return out;
    }

    private float scale() {
        matrix.getValues(values);
        return values[Matrix.MSCALE_X];
    }

    /** Scales the photo to just cover the frame, centred. */
    private void fit() {
        if (bitmap == null || frame.isEmpty()) return;
        float bw = bitmap.getWidth();
        float bh = bitmap.getHeight();
        minScale = Math.max(frame.width() / bw, frame.height() / bh);
        matrix.setScale(minScale, minScale);
        matrix.postTranslate(frame.centerX() - bw * minScale / 2f, frame.centerY() - bh * minScale / 2f);
    }

    private void keepCovered() {
        tmp.set(0, 0, bitmap.getWidth(), bitmap.getHeight());
        matrix.mapRect(tmp);
        float dx = 0;
        float dy = 0;
        if (tmp.left > frame.left) dx = frame.left - tmp.left;
        else if (tmp.right < frame.right) dx = frame.right - tmp.right;
        if (tmp.top > frame.top) dy = frame.top - tmp.top;
        else if (tmp.bottom < frame.bottom) dy = frame.bottom - tmp.bottom;
        matrix.postTranslate(dx, dy);
    }

    @Override protected void onSizeChanged(int w, int h, int ow, int oh) {
        float side = Math.min(w, h) - Toon.dp(getContext(), 36);
        frame.set((w - side) / 2f, (h - side) / 2f, (w + side) / 2f, (h + side) / 2f);
        shade.reset();
        shade.setFillType(Path.FillType.EVEN_ODD);
        shade.addRect(0, 0, w, h, Path.Direction.CW);
        shade.addRoundRect(frame, radius, radius, Path.Direction.CW);
        fit();
    }

    @Override public boolean onTouchEvent(MotionEvent e) {
        scaler.onTouchEvent(e);
        gestures.onTouchEvent(e);
        int a = e.getActionMasked();
        boolean now = a != MotionEvent.ACTION_UP && a != MotionEvent.ACTION_CANCEL;
        if (now != touching) {
            touching = now;
            invalidate();
        }
        return true;
    }

    @Override protected void onDraw(Canvas c) {
        float ink = Toon.dp(getContext(), 3);
        if (bitmap != null) {
            c.drawBitmap(bitmap, matrix, bmpPaint);
        } else {
            paint.setStyle(Paint.Style.FILL);
            paint.setColor(Toon.LILAC);
            paint.setTextSize(Toon.dp(getContext(), 18));
            c.drawText(message, frame.centerX(), frame.centerY(), paint);
        }

        paint.setStyle(Paint.Style.FILL);
        paint.setColor(0xB8231C36);
        c.drawPath(shade, paint);

        if (caption != null && bitmap != null) {
            caption.draw(c, captionPaint, Toon.bold(getContext()), frame.left, frame.top, frame.width());
        }

        if (touching && bitmap != null) {
            paint.setStyle(Paint.Style.STROKE);
            paint.setStrokeWidth(ink * 0.5f);
            paint.setColor(0x80FFF4DE);
            for (int i = 1; i < 3; i++) {
                float x = frame.left + frame.width() * i / 3f;
                float y = frame.top + frame.height() * i / 3f;
                c.drawLine(x, frame.top, x, frame.bottom, paint);
                c.drawLine(frame.left, y, frame.right, y, paint);
            }
        }

        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(ink * 2.6f);
        paint.setColor(Toon.INK);
        c.drawRoundRect(frame, radius, radius, paint);
        paint.setStrokeWidth(ink * 1.3f);
        paint.setColor(Toon.CREAM);
        c.drawRoundRect(frame, radius, radius, paint);

        // Sun-yellow corner brackets.
        float len = Toon.dp(getContext(), 30);
        float o = ink * 1.6f;
        RectF f = new RectF(frame.left - o, frame.top - o, frame.right + o, frame.bottom + o);
        float r = radius + o;
        Path p = new Path();
        p.moveTo(f.left, f.top + len); p.lineTo(f.left, f.top + r);
        p.quadTo(f.left, f.top, f.left + r, f.top); p.lineTo(f.left + len, f.top);
        p.moveTo(f.right - len, f.top); p.lineTo(f.right - r, f.top);
        p.quadTo(f.right, f.top, f.right, f.top + r); p.lineTo(f.right, f.top + len);
        p.moveTo(f.right, f.bottom - len); p.lineTo(f.right, f.bottom - r);
        p.quadTo(f.right, f.bottom, f.right - r, f.bottom); p.lineTo(f.right - len, f.bottom);
        p.moveTo(f.left + len, f.bottom); p.lineTo(f.left + r, f.bottom);
        p.quadTo(f.left, f.bottom, f.left, f.bottom - r); p.lineTo(f.left, f.bottom - len);
        paint.setStrokeWidth(ink * 3f);
        paint.setColor(Toon.INK);
        c.drawPath(p, paint);
        paint.setStrokeWidth(ink * 1.6f);
        paint.setColor(Toon.SUN);
        c.drawPath(p, paint);
    }
}
