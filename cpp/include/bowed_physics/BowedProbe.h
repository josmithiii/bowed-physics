#ifndef NCBS_BOWED_PROBE_H
#define NCBS_BOWED_PROBE_H

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

  // p ranges from 0 to nsamples-1 along the string
  StkFloat stringVelocityAtPosition(int p);
};

} // namespace stk

#endif
