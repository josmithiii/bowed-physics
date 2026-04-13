#include "bowed_physics/BowedProbe.h"

namespace stk {

// Transliteration of the 1997 appendix code to modern STK:
//   bridgeDelay->delay()              -> bridgeDelay_.getDelay()
//   bridgeDelay->contentsAtNowMinus() -> bridgeDelay_.tapOut()
//   bridgeDelay->lastOut()            -> bridgeDelay_.lastOut()
std::pair<StkFloat, StkFloat>
BowedProbe::stringVelocityWavesAtPosition(int p)
{
  int bdelrt = (int)bridgeDelay_.getDelay() + 1; // bow->bridge->bow + p.l. delay
  int ndelrt = (int)neckDelay_.getDelay()   + 1; // bow->nut->bow    + p.l. delay
  int bdel   = bdelrt >> 1;                      // spatial samples bridge->bow
  int ndx    = bdel - p;                         // (0:N-1) -> delay (1:N) on left
  StkFloat leftGoingAtP;
  StkFloat rightGoingAtP;

  if (p < bdel) {
    // Bridge is on the left, nut on the right; "now" is at the bow.
    // Position zero is at far left = half way along delay line.
    leftGoingAtP = bridgeDelay_.tapOut(ndx);
    int rndx = bdelrt - ndx + 1;
    if (rndx < bdelrt) { // last-sample delay lives in lastOut
      rightGoingAtP = -bridgeDelay_.tapOut(rndx);
    } else {
      rightGoingAtP = -bridgeDelay_.lastOut();
    }
  } else { // nut side
    ndx = p - bdel + 1;
    rightGoingAtP = neckDelay_.tapOut(ndx);
    int lndx = ndelrt - ndx + 1;
    if (lndx < ndelrt) {
      leftGoingAtP = -neckDelay_.tapOut(lndx);
    } else {
      leftGoingAtP = -neckDelay_.lastOut();
    }
  }
  return std::make_pair(rightGoingAtP, leftGoingAtP);
}

StkFloat BowedProbe::stringVelocityAtPosition(int p)
{
  std::pair<StkFloat, StkFloat> w = stringVelocityWavesAtPosition(p);
  return w.first + w.second;  // v⁺ + v⁻
}

StkFloat BowedProbe::stringForceAtPosition(int p)
{
  std::pair<StkFloat, StkFloat> w = stringVelocityWavesAtPosition(p);
  return w.first - w.second;  // v⁺ - v⁻  (with R = 1)
}

std::pair<StkFloat, StkFloat>
BowedProbe::stringForceWavesAtPosition(int p)
{
  std::pair<StkFloat, StkFloat> w = stringVelocityWavesAtPosition(p);
  return std::make_pair(w.first, -w.second);  // {f⁺, f⁻} with R = 1
}

} // namespace stk
