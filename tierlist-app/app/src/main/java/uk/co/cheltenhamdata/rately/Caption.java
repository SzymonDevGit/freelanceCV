package uk.co.cheltenhamdata.rately;

import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Typeface;

import org.json.JSONException;
import org.json.JSONObject;

/**
 * Text laid over a picture. Stored apart from the image so it stays editable;
 * position and size are fractions of the picture's side, so the caption looks
 * the same on a small board thumbnail as on the big rating card.
 */
final class Caption {

    /** Text heights for Small, Medium and Large, as a fraction of the picture's side. */
    static final float[] SIZES = {0.09f, 0.13f, 0.19f};
    static final int[] COLORS = {
            0xFFFFFFFF, Toon.SUN, Toon.CORAL, 0xFFFF9F43, 0xFF8BD17C, 0xFF5EC8D8, 0xFFB084F5, 0xFFFF8FC7,
    };
    static final int MAX_LINES = 3;

    String text = "";
    /** Centre of the text block. */
    float x = 0.5f;
    float y = 0.82f;
    float size = SIZES[1];
    int color = COLORS[0];

    boolean isEmpty() {
        return text == null || text.trim().isEmpty();
    }

    Caption copy() {
        Caption c = new Caption();
        c.text = text;
        c.x = x;
        c.y = y;
        c.size = size;
        c.color = color;
        return c;
    }

    JSONObject toJson() throws JSONException {
        JSONObject o = new JSONObject();
        o.put("t", text);
        o.put("x", x);
        o.put("y", y);
        o.put("s", size);
        o.put("c", color);
        return o;
    }

    /** Null when there is no caption or it has no text. */
    static Caption fromJson(JSONObject o) {
        if (o == null) return null;
        Caption c = new Caption();
        c.text = o.optString("t", "");
        c.x = (float) o.optDouble("x", 0.5);
        c.y = (float) o.optDouble("y", 0.82);
        c.size = (float) o.optDouble("s", SIZES[1]);
        c.color = o.optInt("c", COLORS[0]);
        return c.isEmpty() ? null : c;
    }

    static Caption fromJson(String s) {
        if (s == null) return null;
        try {
            return fromJson(new JSONObject(s));
        } catch (JSONException e) {
            return null;
        }
    }

    String toJsonString() {
        try {
            return toJson().toString();
        } catch (JSONException e) {
            return null;
        }
    }

    /**
     * Draws the caption over a square picture whose top-left is (left, top):
     * chunky text with an ink outline and a hard drop shadow, shrunk if needed so
     * it never runs off the picture.
     */
    void draw(Canvas c, Paint p, Typeface font, float left, float top, float side) {
        if (isEmpty()) return;
        String[] lines = text.trim().split("\n");
        p.setTypeface(font);
        p.setTextAlign(Paint.Align.CENTER);
        p.setStrokeJoin(Paint.Join.ROUND);
        p.setTextSize(size * side);

        float widest = 0;
        for (String l : lines) widest = Math.max(widest, p.measureText(l));
        float maxW = side * 0.92f;
        if (widest > maxW) {
            p.setTextSize(p.getTextSize() * maxW / widest);
            widest = maxW;
        }
        Paint.FontMetrics fm = p.getFontMetrics();
        float lineH = (fm.descent - fm.ascent) * 0.92f;
        float blockH = lineH * lines.length;
        float outline = Math.max(1f, p.getTextSize() * 0.09f);
        float drop = outline * 0.85f;

        // Keep the whole block on the picture, whatever the stored position.
        float halfW = widest / 2f + outline;
        float halfH = blockH / 2f + outline;
        float cx = clamp(left + x * side, left + halfW, left + side - halfW - drop);
        float cy = clamp(top + y * side, top + halfH, top + side - halfH - drop);
        float baseline = cy - blockH / 2f - fm.ascent - (lineH - (fm.descent - fm.ascent)) / 2f;

        p.setStyle(Paint.Style.FILL_AND_STROKE);
        p.setStrokeWidth(outline * 2);
        p.setColor(Toon.INK);
        for (int i = 0; i < lines.length; i++) c.drawText(lines[i], cx + drop, baseline + i * lineH + drop, p);
        for (int i = 0; i < lines.length; i++) c.drawText(lines[i], cx, baseline + i * lineH, p);
        p.setStyle(Paint.Style.FILL);
        p.setColor(color);
        for (int i = 0; i < lines.length; i++) c.drawText(lines[i], cx, baseline + i * lineH, p);
    }

    private static float clamp(float v, float lo, float hi) {
        if (lo > hi) return (lo + hi) / 2f;
        return Math.max(lo, Math.min(hi, v));
    }
}
