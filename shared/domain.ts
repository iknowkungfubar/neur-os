// ponytail: shared TypeScript domain types. Mirror of Python backend/domain/entities.py.
// Used by both mobile (React Native) and web.
// Validated by backend/test_domain_sync.py — keep exports in sync.

export class EnergyBattery {
  percentage: number;
  drainRate: number;
  chargeRate: number;

  constructor(percentage = 50, drainRate = 0.5, chargeRate = 0.3) {
    this.percentage = Math.max(0, Math.min(100, percentage));
    this.drainRate = Math.max(0, Math.min(1, drainRate));
    this.chargeRate = Math.max(0, Math.min(1, chargeRate));
  }

  drain(amount: number): number {
    this.percentage = Math.max(0, this.percentage - amount);
    return this.percentage;
  }

  charge(amount: number): number {
    this.percentage = Math.min(100, this.percentage + amount * this.chargeRate);
    return this.percentage;
  }

  tick(hours = 1.0): number {
    this.percentage = Math.max(0, this.percentage - this.drainRate * hours);
    return this.percentage;
  }

  get trafficLight(): string {
    if (this.percentage >= 60) return 'green';
    if (this.percentage >= 20) return 'amber';
    return 'red';
  }

  get asDict(): Record<string, number | string> {
    return { percentage: Math.round(this.percentage * 10) / 10, drainRate: this.drainRate, chargeRate: this.chargeRate, trafficLight: this.trafficLight };
  }
}

export function energyEnvelope(currentPct: number, tasksToday: number, history: number[]): Record<string, number | string> {
  const avgDailyDrain = 0.3;
  const currentUsage = tasksToday * avgDailyDrain;
  const recommendedMax = currentPct * 0.8;
  const recommendedMin = currentPct * 0.15;
  let status = 'ok';
  if (tasksToday > 0 && currentUsage > recommendedMax) status = 'over';
  else if (currentPct <= 20) status = 'low';
  return { recommendedMax: Math.round(recommendedMax * 10) / 10, recommendedMin: Math.round(recommendedMin * 10) / 10, currentUsage: Math.round(currentUsage * 10) / 10, status };
}

export function detectBoomBust(history: number[]): Record<string, any> {
  if (history.length < 5) return { pattern: 'stable', confidence: 0.0, message: 'Not enough data yet' };
  const recent = history.slice(-5);
  const highDays = recent.slice(0, 3).filter(h => h >= 60).length;
  const lowDays = recent.slice(3).filter(h => h < 30).length;
  if (highDays >= 2 && lowDays >= 2) {
    return { pattern: 'boom-bust', confidence: Math.min((highDays + lowDays) / 5, 1.0), message: "You've been pushing hard. Tomorrow might feel rough. Want to schedule rest?" };
  }
  if (recent.length >= 3 && recent.every((h, i) => i === 0 || h < recent[i - 1])) {
    return { pattern: 'declining', confidence: 0.6, message: 'Your energy has been decreasing. A rest day might help.' };
  }
  return { pattern: 'stable', confidence: 0.5, message: 'Energy pattern looks consistent.' };
}
