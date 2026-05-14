/** Call only from `useEffect` (or other client-only code). Never during render — avoids SSR hydration mismatches. */
export function getOrCreateUserId(): string {
  let userId = localStorage.getItem('userId');
  if (!userId) {
    userId = `user_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
    localStorage.setItem('userId', userId);
  }
  return userId;
}

export const formatTime = (time: string): string => {
  if (!time) return '';
  
  // Check if already formatted (contains AM/PM or a.m./p.m.)
  if (time.includes('AM') || time.includes('PM') || time.includes('am') || time.includes('pm')) {
    return time; // Already formatted, return as-is
  }
  
  // Format from 24-hour (HH:MM)
  const [hours, minutes] = time.split(':');
  const hour = parseInt(hours, 10);
  const isAm = hour < 12;
  const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
  return `${displayHour}:${minutes} ${isAm ? 'AM' : 'PM'}`;
};

export const isToday = (date: Date): boolean => {
  const today = new Date();
  return (
    date.getDate() === today.getDate() &&
    date.getMonth() === today.getMonth() &&
    date.getFullYear() === today.getFullYear()
  );
};

export const isTomorrow = (date: Date): boolean => {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return (
    date.getDate() === tomorrow.getDate() &&
    date.getMonth() === tomorrow.getMonth() &&
    date.getFullYear() === tomorrow.getFullYear()
  );
};
