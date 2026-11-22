import { afterEach, describe, expect, it, vi } from "vitest";
import { svgToPng } from "./svgToPng";

describe("UI-M10-PNG adapter", () => {
  afterEach(() => vi.restoreAllMocks());

  it("uses the rendered SVG, inlines styles/title/legend, and emits a >=1320px PNG", async () => {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 760 300");
    const axis = document.createElementNS("http://www.w3.org/2000/svg", "line");
    axis.setAttribute("class", "chart-axis");
    svg.append(axis);
    const tick = document.createElementNS("http://www.w3.org/2000/svg", "text");
    tick.setAttribute("class", "chart-label chart-tick-label");
    tick.setAttribute("x", "370");
    tick.textContent = "1/1 23:00";
    svg.append(tick);
    let sourceBlob: Blob | undefined;
    vi.spyOn(URL, "createObjectURL").mockImplementation((value) => {
      if (value instanceof Blob && value.type.startsWith("image/svg"))
        sourceBlob = value;
      return "blob:test";
    });
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    class FakeImage {
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      set src(_value: string) {
        queueMicrotask(() => this.onload?.());
      }
    }
    vi.stubGlobal("Image", FakeImage);
    const canvas = document.createElement("canvas");
    Object.defineProperty(canvas, "getContext", {
      value: () => ({ fillStyle: "", fillRect: vi.fn(), drawImage: vi.fn() }),
    });
    Object.defineProperty(canvas, "toBlob", {
      value: (callback: BlobCallback) =>
        callback(new Blob(["png"], { type: "image/png" })),
    });
    const createElement = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation(
      (tagName, options) =>
        tagName === "canvas" ? canvas : createElement(tagName, options),
    );

    const result = await svgToPng(svg, {
      title: "History title",
      legend: "Valid · UTC-05:00",
    });
    expect(result.type).toBe("image/png");
    expect(sourceBlob).toBeDefined();
    if (sourceBlob === undefined)
      throw new Error("SVG source Blob was not created");
    const blobToRead: Blob = sourceBlob;
    const serialized = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = () => reject(reader.error);
      reader.readAsText(blobToRead);
    });
    expect(serialized).toContain('viewBox="0 0 1320 589"');
    expect(serialized).toContain('viewBox="0 0 760 300"');
    expect(serialized).toContain('width="1320"');
    expect(serialized).toContain('preserveAspectRatio="xMidYMid meet"');
    expect(serialized).toContain("History title");
    expect(serialized).toContain("Valid · UTC-05:00");
    expect(serialized).toContain(".chart-axis");
  });
});
