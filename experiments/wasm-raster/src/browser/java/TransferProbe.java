import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.IntBuffer;
import org.teavm.jso.JSBody;
import org.teavm.jso.JSBuffer;
import org.teavm.jso.JSBufferType;
import org.teavm.jso.JSObject;

/** Compare transport only, using the unchanged native edge kernel and original scene. */
public final class TransferProbe {
    private static final int SAMPLES = 7;

    @JSBody(params = {"w", "h"}, script = "const c=document.getElementById('frame'); c.width=w; c.height=h;")
    static native void size(int width, int height);

    // Ordinary primitive-array marshalling deliberately copies from the Wasm GC array.
    @JSBody(params = {"words"}, script = "return words;")
    static native JSObject bulk(int[] words);

    // Only the direct buffer can be exposed as a linear-memory typed-array view.
    @JSBody(params = {"words"}, script = "return words;")
    static native JSObject direct(@JSBuffer(JSBufferType.INT32) IntBuffer words);

    @JSBody(params = {"words", "w", "h"}, script = "document.getElementById('frame').getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(words.buffer,words.byteOffset,words.byteLength),w,h),0,0);")
    static native void present(JSObject words, int width, int height);

    @JSBody(params = {"words"}, script = "let h=0x811c9dc5; for(let i=0;i<words.length;i++)h=Math.imul(h^words[i],0x01000193); return h|0;")
    static native int transferredHash(JSObject words);

    @JSBody(script = "const c=document.getElementById('frame'); const a=c.getContext('2d').getImageData(0,0,c.width,c.height).data; let h=0x811c9dc5; for(let i=0;i<a.length;i++)h=Math.imul(h^a[i],0x01000193); return h|0;")
    static native int canvasHash();

    static double median(double[] values) {
        java.util.Arrays.sort(values);
        return values[values.length / 2];
    }

    public static void main(String[] args) {
        StringBuilder result = new StringBuilder("{\"runtime\":\"teavm-0.16.0-wasmgc\",\"sizes\":[");
        StringBuilder comparisons = new StringBuilder();
        int[][] sizes = {{765, 503}, {1280, 800}};
        for (int s=0; s<sizes.length; s++) {
            int width=sizes[s][0], height=sizes[s][1], count=width*height;
            int[] framebuffer=new int[count], rgba=new int[count];
            size(width,height);
            result.append(s==0?"":",").append(Bench.measure(RasterProbe::now,new VerbatimRaster(new NativeFaceKernel()),width,height,framebuffer));
            for(int i=0;i<count;i++)rgba[i]=RasterProbe.toRgbaWord(framebuffer[i]);
            int expected=Scene.hash(rgba), referenceCanvas=0;
            JSObject perPixel=RasterProbe.newInt32Array(count);
            IntBuffer buffer=ByteBuffer.allocateDirect(count*4).order(ByteOrder.LITTLE_ENDIAN).asIntBuffer();
            for (int variant=0;variant<3;variant++) {
                double[] conversion=new double[SAMPLES-1], transfer=new double[SAMPLES-1], upload=new double[SAMPLES-1], total=new double[SAMPLES-1];
                int canvas=0;
                for(int frame=0;frame<SAMPLES;frame++) {
                    double t0=RasterProbe.now();
                    if(variant==0) {
                        for(int i=0;i<count;i++)RasterProbe.put(perPixel,i,RasterProbe.toRgbaWord(framebuffer[i]));
                    } else if(variant==1) {
                        for(int i=0;i<count;i++)rgba[i]=RasterProbe.toRgbaWord(framebuffer[i]);
                    } else {
                        for(int i=0;i<count;i++)buffer.put(i,RasterProbe.toRgbaWord(framebuffer[i]));
                    }
                    double t1=RasterProbe.now();
                    JSObject words=variant==0?perPixel:variant==1?bulk(rgba):direct(buffer);
                    double t2=RasterProbe.now();
                    present(words,width,height);
                    double t3=RasterProbe.now();
                    if(transferredHash(words)!=expected)throw new AssertionError("Pixel transport mismatch: "+variant);
                    canvas=canvasHash();
                    if(variant==0)referenceCanvas=canvas;
                    else if(canvas!=referenceCanvas)throw new AssertionError("Canvas mismatch: "+variant);
                    if(frame>0) {
                        conversion[frame-1]=t1-t0;transfer[frame-1]=t2-t1;
                        upload[frame-1]=t3-t2;total[frame-1]=t3-t0;
                    }
                }
                if(comparisons.length()>0)comparisons.append(',');
                comparisons.append("{\"size\":\"").append(width).append('x').append(height)
                    .append("\",\"variant\":\"").append(new String[]{"per-pixel-js","bulk-array-copy","direct-nio"}[variant])
                    .append("\",\"rgbaFnv1a\":\"").append(Integer.toHexString(expected))
                    .append("\",\"canvasByteFnv1a\":\"").append(Integer.toHexString(canvas))
                    .append("\",\"conversionMedianMs\":").append(median(conversion))
                    .append(",\"transferMedianMs\":").append(median(transfer))
                    .append(",\"uploadMedianMs\":").append(median(upload))
                    .append(",\"totalMedianMs\":").append(median(total)).append('}');
                if(variant==2)result.append(",{\"size\":\"").append(width).append('x').append(height)
                    .append("\",\"convertMs\":").append(median(conversion)+median(transfer))
                    .append(",\"putImageDataMs\":").append(median(upload)).append('}');
            }
        }
        result.append("],\"transferComparisons\":[").append(comparisons).append("]}");
        RasterProbe.report(result.toString());
    }
}
