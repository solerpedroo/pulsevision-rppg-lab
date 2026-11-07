import { describe, expect, it } from "vitest";
import Ajv from "ajv/dist/2020";
import schema from "../../../packages/rppg_types/schemas/RGBSample.json";
import fixture from "../../../tests/fixtures/contracts.json";
const validate = new Ajv({ strict: true }).compile(schema);
describe("shared RGB contract", () => {
  it("accepts the Python fixture", () => {
    expect(validate(fixture.sample)).toBe(true);
  });
  it("rejects out-of-range RGB", () => {
    expect(validate({ ...fixture.sample, rgb_mean: [256, 0, 0] })).toBe(false);
  });
});
