// seestr.cpp — C++ port of the 1997 appendix driver.
//
// Plays one bowed-string note with stk::Bowed and writes two WAV files
// plus a small text metadata file. With a filename prefix all three
// output files are prefixed, so multiple experiments can coexist in
// the same build directory.
//
// Files written (with empty prefix):
//   bowed_out.wav    — body-filtered audio output
//   string_out.wav   — snapshots of string displacement along the string,
//                      one snapshot of length `ilen` written consecutively
//   seestr_meta.txt  — space-separated: fs ilen stride nFrames freq beta
//
// Usage:
//   seestr [duration [stride [beta [prefix]]]]
//     duration : simulated seconds                     (default 0.5)
//     stride   : emit a snapshot every `stride` audio samples (default 20)
//     beta     : bow position ratio (bridgeDelay / totalDelay),
//                in (0,1). STK default is 0.127236 (near the bridge).
//                Use 0.3333 to bow at 1/3 of the string length.
//     prefix   : prepended to all three output filenames   (default "")
//
// The string-state assembly loop is the 1997 appendix fragment adapted
// to modern STK. Velocity integration runs every audio sample (else the
// waveguide's audio-rate velocity aliases into the integral and drifts);
// `stride` only decimates which snapshots get written.

#include "bowed_physics/BowedProbe.h"
#include "FileWvOut.h"

#ifndef BP_STK_RAWWAVES_PATH
#define BP_STK_RAWWAVES_PATH "./external/stk/rawwaves/"
#endif

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

using namespace stk;

int main(int argc, char** argv)
{
  Stk::setSampleRate(44100.0);
  Stk::setRawwavePath(BP_STK_RAWWAVES_PATH);

  const StkFloat    duration = (argc > 1) ? std::atof(argv[1]) : 0.5;
  const int         stride   = (argc > 2) ? std::atoi(argv[2]) : 20;
  const StkFloat    beta     = (argc > 3) ? std::atof(argv[3]) : 0.127236;
  const std::string prefix   = (argc > 4) ? argv[4] : "";

  if (duration <= 0.0 || stride < 1 || beta <= 0.0 || beta >= 1.0) {
    std::cerr << "*** bad args: need duration>0, stride>=1, 0<beta<1\n";
    return 1;
  }

  const StkFloat freq = 220.0;                                // A3
  const StkFloat amp  = 0.7;
  const int      ilen = (int)(Stk::sampleRate() / freq / 2.0);   // bdel+ndel
  const int      warmupSamples = 4000;                           // past ADSR attack
  const StkFloat bowPressureCC = 128.0;                          // max sticking
  const StkFloat vscale = 1.0;
  const StkFloat STRINGSCALING = 0.5;
  const StkFloat ONE_OVER_SRATE = 1.0 / Stk::sampleRate();

  const int totalSamples = (int)(duration * Stk::sampleRate());
  const int nFrames = totalSamples / stride;

  BowedProbe vln;
  vln.noteOn(freq, amp);
  vln.controlChange(2, bowPressureCC);    // __SK_BowPressure_ → slope 1.0
  vln.controlChange(4, beta * 128.0);     // __SK_BowPosition_ → betaRatio

  for (int i = 0; i < warmupSamples; ++i) (void)vln.tick();

  FileWvOut audioOut (prefix + "bowed_out",  1, FileWrite::FILE_WAV, Stk::STK_SINT16);
  FileWvOut stringOut(prefix + "string_out", 1, FileWrite::FILE_WAV, Stk::STK_FLOAT32);

  std::vector<StkFloat> stringState(ilen, 0.0);

  for (int i = 0; i < totalSamples; ++i) {
    StkFloat y = vln.tick();
    audioOut.tick(y);
    const bool emit = (i % stride == 0);
    for (int j = 0; j < ilen; ++j) {
      StkFloat v = vscale * vln.stringVelocityAtPosition(j);
      stringState[j] += v * ONE_OVER_SRATE;
      if (emit) stringOut.tick(STRINGSCALING * stringState[j]);
    }
  }

  vln.noteOff(0.5);

  const std::string metaPath = prefix + "seestr_meta.txt";
  {
    std::ofstream meta(metaPath);
    if (!meta) {
      std::cerr << "*** failed to write " << metaPath << '\n';
      return 1;
    }
    meta << Stk::sampleRate() << ' '
         << ilen << ' '
         << stride << ' '
         << nFrames << ' '
         << freq << ' '
         << beta << '\n';
  }

  std::cout << "duration=" << duration << "s  stride=" << stride
            << "  beta=" << beta
            << "  nFrames=" << nFrames << "  ilen=" << ilen
            << "  dt_per_frame=" << (stride * ONE_OVER_SRATE * 1e3) << " ms\n";
  std::cout << "Wrote " << prefix << "bowed_out.wav, "
            << prefix << "string_out.wav, " << metaPath << '\n';
  return 0;
}
