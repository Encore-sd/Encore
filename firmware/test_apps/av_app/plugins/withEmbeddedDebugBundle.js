// Bundles the JS into debug APKs too, so a build launched from Android Studio
// runs without a Metro dev server (the phone is on the board's WiFi, not the PC's).
// If Metro is running and reachable (e.g. over USB with adb reverse), it is still used.
const { withAppBuildGradle } = require('expo/config-plugins');

module.exports = function withEmbeddedDebugBundle(config) {
  return withAppBuildGradle(config, (config) => {
    const gradle = config.modResults.contents;
    if (!gradle.includes('debuggableVariants = []')) {
      config.modResults.contents = gradle.replace(/^react \{\n/m, 'react {\n    debuggableVariants = []\n');
    }
    return config;
  });
};
