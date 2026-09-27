package uk.co.cheltenhamdata.rately;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.Rect;
import android.media.ExifInterface;
import android.net.Uri;
import android.os.Build;

import java.io.Closeable;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.UUID;

/** Decoding picked photos the right way up, and saving square crops. */
final class Images {

    /** Side of the saved square pictures, in pixels. */
    static final int OUT_SIZE = 720;
    /** Photos are decoded no larger than this for cropping. */
    static final int MAX_SIDE = 2048;

    private Images() {}

    static Bitmap load(Context c, Uri uri) throws IOException {
        BitmapFactory.Options bounds = new BitmapFactory.Options();
        bounds.inJustDecodeBounds = true;
        InputStream in = c.getContentResolver().openInputStream(uri);
        try {
            BitmapFactory.decodeStream(in, null, bounds);
        } finally {
            close(in);
        }
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null;

        BitmapFactory.Options o = new BitmapFactory.Options();
        o.inSampleSize = 1;
        while (Math.max(bounds.outWidth, bounds.outHeight) / o.inSampleSize > MAX_SIDE) o.inSampleSize *= 2;
        in = c.getContentResolver().openInputStream(uri);
        Bitmap b;
        try {
            b = BitmapFactory.decodeStream(in, null, o);
        } finally {
            close(in);
        }
        if (b == null) return null;
        return orient(b, exifOrientation(c, uri));
    }

    private static int exifOrientation(Context c, Uri uri) {
        InputStream in = null;
        try {
            in = c.getContentResolver().openInputStream(uri);
            if (in == null) return ExifInterface.ORIENTATION_NORMAL;
            ExifInterface exif;
            if (Build.VERSION.SDK_INT >= 24) {
                // ExifInterface(InputStream) arrived in API 24; the app compiles against 23.
                exif = ExifInterface.class.getConstructor(InputStream.class).newInstance(in);
            } else {
                File tmp = new File(c.getCacheDir(), "exif.tmp");
                copy(in, tmp);
                exif = new ExifInterface(tmp.getAbsolutePath());
                if (!tmp.delete()) tmp.deleteOnExit();
            }
            return exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL);
        } catch (Exception e) {
            return ExifInterface.ORIENTATION_NORMAL;
        } finally {
            close(in);
        }
    }

    private static Bitmap orient(Bitmap b, int orientation) {
        Matrix m = new Matrix();
        switch (orientation) {
            case ExifInterface.ORIENTATION_FLIP_HORIZONTAL: m.setScale(-1, 1); break;
            case ExifInterface.ORIENTATION_ROTATE_180: m.setRotate(180); break;
            case ExifInterface.ORIENTATION_FLIP_VERTICAL: m.setScale(1, -1); break;
            case ExifInterface.ORIENTATION_TRANSPOSE: m.setRotate(90); m.postScale(-1, 1); break;
            case ExifInterface.ORIENTATION_ROTATE_90: m.setRotate(90); break;
            case ExifInterface.ORIENTATION_TRANSVERSE: m.setRotate(-90); m.postScale(-1, 1); break;
            case ExifInterface.ORIENTATION_ROTATE_270: m.setRotate(-90); break;
            default: return b;
        }
        Bitmap r = Bitmap.createBitmap(b, 0, 0, b.getWidth(), b.getHeight(), m, true);
        if (r != b) b.recycle();
        return r;
    }

    static Bitmap rotate90(Bitmap b) {
        Matrix m = new Matrix();
        m.setRotate(90);
        return Bitmap.createBitmap(b, 0, 0, b.getWidth(), b.getHeight(), m, true);
    }

    /** The largest centred square, scaled to size x size. */
    static Bitmap centerCrop(Bitmap b, int size) {
        int side = Math.min(b.getWidth(), b.getHeight());
        int left = (b.getWidth() - side) / 2;
        int top = (b.getHeight() - side) / 2;
        Bitmap out = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(out);
        c.drawColor(Color.WHITE);
        c.drawBitmap(b, new Rect(left, top, left + side, top + side), new Rect(0, 0, size, size),
                new Paint(Paint.FILTER_BITMAP_FLAG | Paint.ANTI_ALIAS_FLAG));
        return out;
    }

    /** Writes a JPEG into the images folder and returns its file name. */
    static String save(Context c, Bitmap b) throws IOException {
        String name = UUID.randomUUID().toString() + ".jpg";
        OutputStream out = new FileOutputStream(Store.image(c, name));
        try {
            if (!b.compress(Bitmap.CompressFormat.JPEG, 90, out)) throw new IOException("compress failed");
        } finally {
            close(out);
        }
        return name;
    }

    private static void copy(InputStream in, File to) throws IOException {
        OutputStream out = new FileOutputStream(to);
        try {
            byte[] buf = new byte[16384];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
        } finally {
            close(out);
        }
    }

    static void close(Closeable c) {
        if (c == null) return;
        try {
            c.close();
        } catch (IOException ignored) {
            // Nothing useful to do.
        }
    }
}
