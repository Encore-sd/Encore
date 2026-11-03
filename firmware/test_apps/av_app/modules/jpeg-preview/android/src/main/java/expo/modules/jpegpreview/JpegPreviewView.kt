package expo.modules.jpegpreview

import android.content.Context
import android.graphics.BitmapFactory
import android.widget.ImageView
import expo.modules.kotlin.AppContext
import expo.modules.kotlin.views.ExpoView
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

// Live JPEG preview: frames are decoded off the UI thread and the previous frame stays on
// screen until the next one is ready, so it never blanks. Frames that arrive while one is
// still decoding are skipped - only the newest is shown.
class JpegPreviewView(context: Context, appContext: AppContext) : ExpoView(context, appContext) {
  // Let Android size the ImageView to this view (React Native doesn't lay out native children)
  override val shouldUseAndroidLayout = true

  private val imageView = ImageView(context).apply {
    scaleType = ImageView.ScaleType.FIT_CENTER
    layoutParams = LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT)
  }
  private val newest = AtomicReference<ByteArray?>(null)
  private val decoding = AtomicBoolean(false)

  init {
    addView(imageView)
  }

  fun showFrame(jpeg: ByteArray) {
    newest.set(jpeg)
    if (decoding.compareAndSet(false, true)) decoder.execute { decodeNewest() }
  }

  private fun decodeNewest() {
    while (true) {
      val jpeg = newest.getAndSet(null)
      if (jpeg == null) {
        decoding.set(false)
        // A frame may have arrived between the check and the reset
        if (newest.get() != null && decoding.compareAndSet(false, true)) continue
        return
      }
      val bitmap = BitmapFactory.decodeByteArray(jpeg, 0, jpeg.size) ?: continue // skip corrupted frames
      post { imageView.setImageBitmap(bitmap) }
    }
  }

  companion object {
    private val decoder = Executors.newSingleThreadExecutor()
  }
}
