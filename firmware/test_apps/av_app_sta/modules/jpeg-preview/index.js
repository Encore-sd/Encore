import { requireNativeView } from 'expo';

// Native live JPEG preview (Android only). Call ref.current.showFrame(jpegBytes) for each frame.
export default requireNativeView('JpegPreview');
