package uk.co.cheltenhamdata.rately;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.graphics.Shader;
import android.view.View;

import java.util.Random;

/**
 * A cartoon version of a dusk camp on the moors: striped purple-to-gold sky,
 * a low sun, rolling hills with ink outlines, dry grass and a little tent.
 */
final class SunsetView extends View {

    private static final int[] SKY = {0xFF3B335A, 0xFF5D4F7F, 0xFF8C7AAE, 0xFFC98B86, 0xFFF4A259, 0xFFFFD23F};
    private static final float[] SKY_AT = {0f, 0.28f, 0.52f, 0.72f, 0.88f, 1f};

    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path far = new Path();
    private final Path mid = new Path();
    private final Path valley = new Path();
    private final Path grass = new Path();
    private final Path tentBody = new Path();
    private final Path tentDoor = new Path();
    private final Path scratch = new Path();
    private final RectF oval = new RectF();
    private final float ink;
    private float horizon = 0.56f;
    private boolean tent = true;
    private float tentX = 0.28f;
    private LinearGradient sky;

    SunsetView(Context c) {
        super(c);
        ink = Toon.dp(c, 2.5f);
        paint.setStrokeJoin(Paint.Join.ROUND);
        paint.setStrokeCap(Paint.Cap.ROUND);
    }

    /** Where the horizon sits, as a fraction of the height. */
    void setHorizon(float f) {
        horizon = f;
        rebuild(getWidth(), getHeight());
        invalidate();
    }

    void setTent(boolean show, float x) {
        tent = show;
        tentX = x;
        invalidate();
    }

    @Override protected void onSizeChanged(int w, int h, int ow, int oh) {
        rebuild(w, h);
    }

    private float ground(int h) {
        return h - h * horizon;
    }

    /** Height of a hill layer's top edge at x: a base line plus two slow waves. */
    private static float wave(float x, float w, float base, float amp, float f1, float p1, float f2, float p2) {
        double t = x / w * Math.PI * 2;
        return base + amp * (float) (0.62 * Math.sin(t * f1 + p1) + 0.38 * Math.sin(t * f2 + p2));
    }

    private float grassTop(float x, int w, int h) {
        float hz = h * horizon;
        float g = ground(h);
        return wave(x, w, hz + g * 0.52f, g * 0.1f, 0.55f, 2.2f, 1.6f, 0.4f);
    }

    private void layer(Path p, int w, int h, float base, float amp, float f1, float p1, float f2, float p2) {
        p.reset();
        float pad = ink * 2;
        p.moveTo(-pad, h + pad);
        int steps = 48;
        for (int i = 0; i <= steps; i++) {
            float x = -pad + (w + pad * 2) * i / steps;
            p.lineTo(x, wave(x, w, base, amp, f1, p1, f2, p2));
        }
        p.lineTo(w + pad, h + pad);
        p.close();
    }

    private void rebuild(int w, int h) {
        if (w == 0 || h == 0) return;
        float hz = h * horizon;
        float g = ground(h);
        sky = new LinearGradient(0, 0, 0, hz, SKY, SKY_AT, Shader.TileMode.CLAMP);
        layer(far, w, h, hz + g * 0.05f, g * 0.05f, 1.3f, 0.3f, 3.1f, 1.1f);
        layer(mid, w, h, hz + g * 0.2f, g * 0.08f, 0.9f, 1.9f, 2.3f, 0.2f);
        layer(valley, w, h, hz + g * 0.36f, g * 0.07f, 0.7f, 4.0f, 2.0f, 2.5f);
        layer(grass, w, h, hz + g * 0.52f, g * 0.1f, 0.55f, 2.2f, 1.6f, 0.4f);
    }

    @Override protected void onDraw(Canvas c) {
        int w = getWidth();
        int h = getHeight();
        if (sky == null) rebuild(w, h);
        float hz = h * horizon;
        float g = ground(h);

        // Sky, and gold below the horizon for the gaps between hills.
        paint.setStyle(Paint.Style.FILL);
        paint.setShader(sky);
        c.drawRect(0, 0, w, hz + 1, paint);
        paint.setShader(null);
        paint.setColor(SKY[SKY.length - 1]);
        c.drawRect(0, hz, w, h, paint);

        drawStars(c, w, hz);
        drawClouds(c, w, hz);

        // Low sun, half hidden behind the far hills.
        float sunR = Math.min(w * 0.11f, g * 0.55f);
        float sunX = w * 0.64f;
        float sunY = hz + g * 0.06f;
        paint.setColor(0x33FFF1A8);
        c.drawCircle(sunX, sunY, sunR * 2.1f, paint);
        paint.setColor(0x55FFE680);
        c.drawCircle(sunX, sunY, sunR * 1.5f, paint);
        paint.setColor(0xFFFFF1A8);
        c.drawCircle(sunX, sunY, sunR, paint);
        outline(c);
        c.drawCircle(sunX, sunY, sunR, paint);

        hill(c, far, 0xFF5A5C84);
        hill(c, mid, 0xFF4B6A5C);
        hill(c, valley, 0xFF34513F);
        hill(c, grass, 0xFF9C8A52);
        drawTufts(c, w, h);
        if (tent) drawTent(c, w * tentX, grassTop(w * tentX, w, h) + g * 0.02f, Math.min(w * 0.2f, g * 0.5f));
    }

    private void outline(Canvas c) {
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(ink);
        paint.setColor(Toon.INK);
    }

    private void hill(Canvas c, Path p, int color) {
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(color);
        c.drawPath(p, paint);
        outline(c);
        c.drawPath(p, paint);
    }

    private void drawStars(Canvas c, int w, float hz) {
        Random r = new Random(7);
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(0xE6FFF4D6);
        for (int i = 0; i < 14; i++) {
            float x = r.nextFloat() * w;
            float y = r.nextFloat() * hz * 0.38f;
            float s = ink * (0.6f + r.nextFloat() * 0.9f);
            scratch.reset();
            scratch.moveTo(x, y - s * 1.6f);
            scratch.quadTo(x, y, x + s * 1.6f, y);
            scratch.quadTo(x, y, x, y + s * 1.6f);
            scratch.quadTo(x, y, x - s * 1.6f, y);
            scratch.quadTo(x, y, x, y - s * 1.6f);
            c.drawPath(scratch, paint);
        }
    }

    private void drawClouds(Canvas c, int w, float hz) {
        // y (fraction of the sky), x start, length (fractions of the width), thickness in stroke units, colour.
        float[][] streaks = {
                {0.16f, -0.12f, 0.55f, 4.2f}, {0.29f, 0.46f, 0.7f, 5f}, {0.47f, 0.04f, 0.5f, 3.8f},
                {0.63f, 0.56f, 0.52f, 4.2f}, {0.79f, -0.06f, 0.46f, 3.4f}, {0.9f, 0.66f, 0.36f, 2.6f},
        };
        int[] colors = {0xFF6B5E8F, 0xFF7E6E9E, 0xFFAE8A9E, 0xFFE09A7E, 0xFFF7B868, 0xFFFFE07A};
        for (int i = 0; i < streaks.length; i++) {
            float[] s = streaks[i];
            float y = hz * s[0];
            float x0 = w * s[1];
            float x1 = x0 + w * s[2];
            float t = ink * s[3];
            oval.set(x0, y - t / 2, x1, y + t / 2);
            paint.setStyle(Paint.Style.FILL);
            paint.setColor(0x402B2340);
            oval.offset(0, t * 0.35f);
            c.drawRoundRect(oval, t / 2, t / 2, paint);
            oval.offset(0, -t * 0.35f);
            paint.setColor(colors[i]);
            c.drawRoundRect(oval, t / 2, t / 2, paint);
        }
    }

    private void drawTufts(Canvas c, int w, int h) {
        Random r = new Random(11);
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(ink * 0.8f);
        paint.setColor(0xFF6E6036);
        float g = ground(h);
        for (int i = 0; i < 18; i++) {
            float x = r.nextFloat() * w;
            float top = grassTop(x, w, h);
            float y = top + (h - top) * (0.25f + r.nextFloat() * 0.65f);
            float s = g * (0.035f + r.nextFloat() * 0.03f);
            c.drawLine(x, y, x - s * 0.6f, y - s, paint);
            c.drawLine(x, y, x, y - s * 1.3f, paint);
            c.drawLine(x, y, x + s * 0.6f, y - s, paint);
        }
    }

    private void drawTent(Canvas c, float x, float base, float s) {
        float hw = s / 2f;
        float th = s * 0.62f;

        // Shadow on the grass.
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(0x552B2340);
        oval.set(x - hw * 1.25f, base - s * 0.05f, x + hw * 1.3f, base + s * 0.08f);
        c.drawOval(oval, paint);

        // Guy lines and pegs.
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(ink * 0.6f);
        paint.setColor(Toon.INK);
        c.drawLine(x - hw * 0.8f, base - th * 0.45f, x - hw * 1.45f, base + s * 0.02f, paint);
        c.drawLine(x + hw * 0.8f, base - th * 0.45f, x + hw * 1.45f, base + s * 0.02f, paint);

        tentBody.reset();
        tentBody.moveTo(x - hw, base);
        tentBody.cubicTo(x - hw, base - th * 0.72f, x - hw * 0.42f, base - th, x, base - th);
        tentBody.cubicTo(x + hw * 0.42f, base - th, x + hw, base - th * 0.72f, x + hw, base);
        tentBody.close();
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(0xFF3F7A5C);
        c.drawPath(tentBody, paint);

        // Lighter left panel.
        c.save();
        c.clipPath(tentBody);
        paint.setColor(0xFF5E9C78);
        scratch.reset();
        scratch.moveTo(x - hw * 1.1f, base);
        scratch.lineTo(x - hw * 1.1f, base - th * 1.1f);
        scratch.lineTo(x - hw * 0.1f, base - th * 1.1f);
        scratch.quadTo(x - hw * 0.55f, base - th * 0.5f, x - hw * 0.42f, base);
        scratch.close();
        c.drawPath(scratch, paint);
        c.restore();

        outline(c);
        c.drawPath(tentBody, paint);
        c.drawLine(x, base - th, x - hw * 0.42f, base, paint);

        // Door, with a lantern glowing inside.
        tentDoor.reset();
        tentDoor.moveTo(x - hw * 0.05f, base);
        tentDoor.cubicTo(x - hw * 0.02f, base - th * 0.45f, x + hw * 0.08f, base - th * 0.66f, x + hw * 0.14f, base - th * 0.7f);
        tentDoor.cubicTo(x + hw * 0.3f, base - th * 0.5f, x + hw * 0.52f, base - th * 0.2f, x + hw * 0.58f, base);
        tentDoor.close();
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(0xFF1E3B2E);
        c.drawPath(tentDoor, paint);
        float lx = x + hw * 0.27f;
        float ly = base - th * 0.2f;
        paint.setColor(0x66FFD23F);
        c.drawCircle(lx, ly, s * 0.085f, paint);
        paint.setColor(0xFFFFD23F);
        c.drawCircle(lx, ly, s * 0.04f, paint);
        outline(c);
        paint.setStrokeWidth(ink * 0.8f);
        c.drawPath(tentDoor, paint);
    }
}
