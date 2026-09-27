package uk.co.cheltenhamdata.rately;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.View;
import android.view.ViewGroup;

/**
 * Lays children out left to right, wrapping onto new rows. While something is
 * dragged over it, it draws a yellow bar where the drop would land.
 */
final class FlowLayout extends ViewGroup {

    private final int gap;
    private int dropIndex = -1;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF bar = new RectF();

    FlowLayout(Context c, int gapPx) {
        super(c);
        gap = gapPx;
        setWillNotDraw(false);
    }

    void setDropIndex(int i) {
        if (i != dropIndex) {
            dropIndex = i;
            invalidate();
        }
    }

    @Override protected void onMeasure(int ws, int hs) {
        int maxW = MeasureSpec.getMode(ws) == MeasureSpec.UNSPECIFIED
                ? Integer.MAX_VALUE : MeasureSpec.getSize(ws) - getPaddingLeft() - getPaddingRight();
        int x = 0;
        int y = 0;
        int rowH = 0;
        int usedW = 0;
        for (int i = 0; i < getChildCount(); i++) {
            View c = getChildAt(i);
            if (c.getVisibility() == GONE) continue;
            measureChild(c, ws, hs);
            int cw = c.getMeasuredWidth();
            int ch = c.getMeasuredHeight();
            if (x > 0 && x + cw > maxW) {
                x = 0;
                y += rowH + gap;
                rowH = 0;
            }
            x += cw + gap;
            rowH = Math.max(rowH, ch);
            usedW = Math.max(usedW, x - gap);
        }
        int w = usedW + getPaddingLeft() + getPaddingRight();
        int h = Math.max(y + rowH + getPaddingTop() + getPaddingBottom(), getSuggestedMinimumHeight());
        setMeasuredDimension(resolveSize(w, ws), resolveSize(h, hs));
    }

    @Override protected void onLayout(boolean changed, int l, int t, int r, int b) {
        int maxW = r - l - getPaddingLeft() - getPaddingRight();
        int x = 0;
        int y = 0;
        int rowH = 0;
        for (int i = 0; i < getChildCount(); i++) {
            View c = getChildAt(i);
            if (c.getVisibility() == GONE) continue;
            int cw = c.getMeasuredWidth();
            int ch = c.getMeasuredHeight();
            if (x > 0 && x + cw > maxW) {
                x = 0;
                y += rowH + gap;
                rowH = 0;
            }
            int left = getPaddingLeft() + x;
            int top = getPaddingTop() + y;
            c.layout(left, top, left + cw, top + ch);
            x += cw + gap;
            rowH = Math.max(rowH, ch);
        }
    }

    /** The child index a drop at (x, y) in this view's coordinates would insert at. */
    int indexAt(float x, float y) {
        int n = getChildCount();
        for (int i = 0; i < n; i++) {
            View c = getChildAt(i);
            if (y > c.getBottom() + gap / 2f) continue;
            if (y < c.getTop() - gap / 2f) return i;
            if (x < (c.getLeft() + c.getRight()) / 2f) return i;
            if (i + 1 < n && getChildAt(i + 1).getTop() > c.getTop()) return i + 1;
        }
        return n;
    }

    @Override protected void dispatchDraw(Canvas canvas) {
        super.dispatchDraw(canvas);
        if (dropIndex < 0) return;
        float w = gap * 0.9f + 2;
        int n = getChildCount();
        float x;
        float top;
        float bottom;
        if (n == 0) {
            x = getPaddingLeft() + w;
            top = getPaddingTop();
            bottom = getHeight() - getPaddingBottom();
        } else if (dropIndex < n) {
            View c = getChildAt(dropIndex);
            x = c.getLeft() - gap / 2f;
            top = c.getTop();
            bottom = c.getBottom();
        } else {
            View c = getChildAt(n - 1);
            x = c.getRight() + gap / 2f;
            top = c.getTop();
            bottom = c.getBottom();
        }
        x = Math.max(w / 2 + 1, Math.min(getWidth() - w / 2 - 1, x));
        bar.set(x - w / 2, top, x + w / 2, bottom);
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(Toon.SUN);
        canvas.drawRoundRect(bar, w, w, paint);
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(Math.max(2, w / 3));
        paint.setColor(Toon.INK);
        canvas.drawRoundRect(bar, w, w, paint);
    }
}
