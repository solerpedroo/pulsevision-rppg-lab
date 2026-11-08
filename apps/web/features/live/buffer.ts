import type { Sample } from "./types";
export class RingBuffer {
  private rows: (Sample | undefined)[];
  private head = 0;
  private size = 0;
  private last = -Infinity;
  constructor(readonly capacity = 900) {
    if (!Number.isInteger(capacity) || capacity < 1)
      throw new Error("invalid_capacity");
    this.rows = new Array(capacity);
  }
  push(row: Sample) {
    if (
      !Number.isFinite(row.timestamp_s) ||
      row.timestamp_s < 0 ||
      row.timestamp_s <= this.last
    )
      throw new Error("invalid_timestamps");
    this.last = row.timestamp_s;
    this.rows[this.head] = row;
    this.head = (this.head + 1) % this.capacity;
    this.size = Math.min(this.size + 1, this.capacity);
  }
  snapshot() {
    return Array.from(
      { length: this.size },
      (_, i) =>
        this.rows[(this.head - this.size + i + this.capacity) % this.capacity]!,
    );
  }
  window(start: number, end: number) {
    return this.snapshot().filter(
      (s) => s.timestamp_s >= start - 1e-9 && s.timestamp_s < end - 1e-9,
    );
  }
  clear() {
    this.rows = new Array(this.capacity);
    this.head = this.size = 0;
    this.last = -Infinity;
  }
}
