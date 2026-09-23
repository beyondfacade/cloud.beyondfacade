import { expect, it } from "vitest";
import { withTopicParticle } from "./korean";

it("받침이 없으면 는, 있으면 은, 한글이 아니면 는", () => {
  expect(withTopicParticle("카페")).toBe("카페는");
  expect(withTopicParticle("미용실")).toBe("미용실은");
  expect(withTopicParticle("PC방")).toBe("PC방은");
  expect(withTopicParticle("gym")).toBe("gym는");
});
