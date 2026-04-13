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
// The string-state assembly loop reconstructs displacement u(x) by
// spatially integrating slope = -force at each emit frame. (The 1997
// appendix version integrated velocity in time per spatial sample,
// which runs N independent integrators with no coupling; any DC
// asymmetry in the bow injection then drives the two halves of the
// string apart, producing a growing *displacement* jump at the bow.)
//
// With R = T = 1, slope u_x = -(v⁺ - v⁻) = -force. Integrating slope
// from j=0 gives u(j). A residual linear ramp is subtracted so both
// endpoints are pinned (u(0) = u(ilen-1) = 0); under exact arithmetic
// that ramp would be zero, so its magnitude is a direct numerical-
// health check.

#include "bowed_physics/BowedProbe.h"
#include "FileWvOut.h"

#ifndef BP_STK_RAWWAVES_PATH
#define BP_STK_RAWWAVES_PATH "./external/stk/rawwaves/"
#endif

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
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
  // Spatial integration of slope accumulates ilen terms, so the raw
  // scale is larger than the old per-sample time-integrator version.
  // This keeps snapshots well inside the [-1,1] WAV range for ilen≈100.
  const StkFloat STRINGSCALING = 0.02;

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

  // Expected endpoint residual from roundoff: each add loses ~0.5 ulp
  // relative, and the sum is over `ilen` terms; under a random-walk
  // model the residual scales as sqrt(ilen)*ulp*peak, worst case
  // ilen*ulp*peak. Warn when we exceed a generous 16*sqrt(ilen) factor.
  const StkFloat ULP = std::numeric_limits<StkFloat>::epsilon();
  const StkFloat noiseFactor = 16.0 * std::sqrt((StkFloat)ilen) * ULP;
  StkFloat worstResidual = 0.0;       // max |uEnd| / peak
  StkFloat worstResidualAbs = 0.0;    // max |uEnd|
  int worstResidualFrame = -1;
  int framesOverThreshold = 0;
  bool reportedFirst = false;

  for (int i = 0; i < totalSamples; ++i) {
    StkFloat y = vln.tick();
    audioOut.tick(y);
    if (i % stride != 0) continue;

    // 1. Spatially integrate slope = -force from j = 0.
    StkFloat u = 0.0;
    StkFloat peak = 0.0;
    for (int j = 0; j < ilen; ++j) {
      stringState[j] = u;
      u += -vln.stringForceAtPosition(j);   // slope, R = T = 1
      peak = std::max(peak, std::fabs(stringState[j]));
    }
    peak = std::max(peak, std::fabs(u));

    // 2. Subtract linear ramp so u(0) = u(ilen-1) = 0. stringState[0]
    //    is already 0 by construction; only the slope needs removing.
    const StkFloat uEnd = stringState[ilen - 1];
    const StkFloat invN = 1.0 / (StkFloat)(ilen - 1);
    for (int j = 0; j < ilen; ++j) {
      stringState[j] -= (StkFloat)j * invN * uEnd;
    }

    // 3. Numerical-health check: how big is the residual we just
    //    subtracted, relative to the peak displacement on the string?
    const StkFloat residualRel = (peak > 0.0) ? std::fabs(uEnd) / peak : 0.0;
    if (residualRel > worstResidual) {
      worstResidual = residualRel;
      worstResidualAbs = std::fabs(uEnd);
      worstResidualFrame = i / stride;
    }
    if (residualRel > noiseFactor) {
      ++framesOverThreshold;
      if (!reportedFirst) {
        std::cerr << "*** spatial-integration residual " << residualRel
                  << " > expected " << noiseFactor
                  << " first at frame " << (i / stride)
                  << " (peak=" << peak << ", uEnd=" << uEnd << ")\n";
        reportedFirst = true;
      }
    }

    for (int j = 0; j < ilen; ++j) {
      stringOut.tick(STRINGSCALING * stringState[j]);
    }
  }

  std::cout << "Worst endpoint residual: |uEnd|=" << worstResidualAbs
            << ", |uEnd|/peak=" << worstResidual
            << " at frame " << worstResidualFrame
            << "  (roundoff threshold " << noiseFactor
            << ", " << framesOverThreshold << "/" << nFrames
            << " frames over)\n";
  if (framesOverThreshold > 0) {
    std::cout << "  note: residual >> roundoff means the raw slope field "
                 "has non-numerical DC (e.g. bow-drive DC in the "
                 "velocity waveguide) — the ramp subtraction is doing "
                 "real work, not just cleaning noise.\n";
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
            << "  dt_per_frame=" << (stride * 1e3 / Stk::sampleRate()) << " ms\n";
  std::cout << "Wrote " << prefix << "bowed_out.wav, "
            << prefix << "string_out.wav, " << metaPath << '\n';
  return 0;
}
