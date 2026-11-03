package expo.modules.jpegpreview

import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

class JpegPreviewModule : Module() {
  override fun definition() = ModuleDefinition {
    Name("JpegPreview")

    View(JpegPreviewView::class) {
      // JS: ref.current.showFrame(jpegBytes) - the bytes arrive as a Uint8Array
      AsyncFunction("showFrame") { view: JpegPreviewView, jpeg: ByteArray ->
        view.showFrame(jpeg)
      }
    }
  }
}
