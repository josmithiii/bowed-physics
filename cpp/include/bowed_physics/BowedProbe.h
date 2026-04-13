#ifndef NCBS_BOWED_PROBE_H
#define NCBS_BOWED_PROBE_H

#include <utility>

#include "Bowed.h"

namespace stk {

// Subclass of stk::Bowed exposing the internal string-state probe
// described in the appendix of the 1997 ICMC paper
// "Nonlinear Commuted Synthesis of Bowed Strings" (J.O. Smith).
//
// Original 1997 code was for the pre-4.x STK (MY_FLOAT, BowedStr,
// pointer-based delay lines, contentsAtNowMinus). This port targets
// modern STK (StkFloat, stack DelayL members, tapOut).
class BowedProbe : public Bowed {
public:
  BowedProbe(StkFloat lowestFrequency = 8.0) : Bowed(lowestFrequency) {}

  // p ranges from 0 to nsamples-1 along the string.
  //
  // All "force" quantities below use the normalization R = T = 1, where
  // R is the transverse wave impedance and T is string tension. Under
  // this normalization, transverse force f = v⁺ - v⁻ and string slope
  // u_x = -f = v⁻ - v⁺.

  // Sum of right- and left-going transverse velocity waves: v(p) = v⁺ + v⁻.
  StkFloat stringVelocityAtPosition(int p);

  // Net transverse force: f(p) = v⁺ - v⁻ (with R = 1).
  StkFloat stringForceAtPosition(int p);

  // Returns {v⁺, v⁻} at position p (right-going, left-going velocity).
  std::pair<StkFloat, StkFloat> stringVelocityWavesAtPosition(int p);

  // Returns {f⁺, f⁻} = {v⁺, -v⁻} at position p (with R = 1).
  std::pair<StkFloat, StkFloat> stringForceWavesAtPosition(int p);
};

} // namespace stk

#endif
