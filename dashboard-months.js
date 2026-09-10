(function (global) {
  'use strict';

  const SUPPORTED_MONTHS = ['2026-09', '2026-10', '2026-11', '2026-12'];
  const FIRST_MONTH = SUPPORTED_MONTHS[0];
  const LAST_MONTH = SUPPORTED_MONTHS[SUPPORTED_MONTHS.length - 1];

  function pad(value) {
    return String(value).padStart(2, '0');
  }

  function localDateKey(date) {
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  }

  function localMonthKey(date) {
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}`;
  }

  function defaultMonth(now) {
    const key = localMonthKey(now);
    if (key <= FIRST_MONTH) return FIRST_MONTH;
    if (key >= LAST_MONTH) return LAST_MONTH;
    return SUPPORTED_MONTHS.includes(key) ? key : FIRST_MONTH;
  }

  function monthMeta(monthKey) {
    if (!SUPPORTED_MONTHS.includes(monthKey)) {
      throw new Error(`Unsupported month: ${monthKey}`);
    }
    const [yearText, monthText] = monthKey.split('-');
    const year = Number(yearText);
    const monthIndex = Number(monthText) - 1;
    const first = new Date(year, monthIndex, 1);
    const days = new Date(year, monthIndex + 1, 0).getDate();
    const label = first.toLocaleString('en-US', { month: 'long', year: 'numeric' });
    return { key: monthKey, label, year, monthIndex, days, firstWeekday: first.getDay() };
  }

  function eventInMonth(dateString, monthKey) {
    return String(dateString || '').slice(0, 7) === monthKey;
  }

  function sameMonth(now, monthKey) {
    return localMonthKey(now) === monthKey;
  }

  function addLocalDays(date, days) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days);
  }

  function currentWeekDateKeys(now) {
    const start = addLocalDays(now, -now.getDay());
    return Array.from({ length: 7 }, (_, index) => localDateKey(addLocalDays(start, index)));
  }

  function currentWeekendDateKeys(now) {
    const start = addLocalDays(now, -now.getDay());
    return [5, 6, 7].map(offset => localDateKey(addLocalDays(start, offset)));
  }

  const api = {
    SUPPORTED_MONTHS,
    defaultMonth,
    monthMeta,
    eventInMonth,
    sameMonth,
    currentWeekDateKeys,
    currentWeekendDateKeys,
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.SFMonths = api;
})(typeof window !== 'undefined' ? window : globalThis);
