import { describe, it, expect } from "vitest"
import { NodeTypeConstants, EdgeTypeConstants } from "../types"

describe("NodeTypeConstants", () => {
  it("defines conversation types", () => {
    expect(NodeTypeConstants.CONVERSATION).toBe("conversation")
    expect(NodeTypeConstants.EXECUTION).toBe("execution")
    expect(NodeTypeConstants.WORKFLOW).toBe("workflow")
  })

  it("defines browser types", () => {
    expect(NodeTypeConstants.BROWSER_SESSION).toBe("browser:session")
    expect(NodeTypeConstants.BROWSER_PAGE).toBe("browser:page")
    expect(NodeTypeConstants.BROWSER_BOOKMARK).toBe("browser:bookmark")
  })

  it("defines voice types", () => {
    expect(NodeTypeConstants.VOICE_SESSION).toBe("voice:session")
    expect(NodeTypeConstants.VOICE_COMMAND).toBe("voice:command")
  })

  it("defines vision types", () => {
    expect(NodeTypeConstants.VISION_CAPTURE).toBe("vision:capture")
    expect(NodeTypeConstants.VISION_ANNOTATION).toBe("vision:annotation")
  })

  it("defines file types", () => {
    expect(NodeTypeConstants.GENERATED_FILE).toBe("file:generated")
    expect(NodeTypeConstants.REFERENCED_FILE).toBe("file:referenced")
  })

  it("defines knowledge types", () => {
    expect(NodeTypeConstants.KNOWLEDGE_STATEMENT).toBe("knowledge:statement")
    expect(NodeTypeConstants.KNOWLEDGE_SUMMARY).toBe("knowledge:summary")
    expect(NodeTypeConstants.KNOWLEDGE_ENTITY).toBe("knowledge:entity")
  })

  it("defines general types", () => {
    expect(NodeTypeConstants.ARTIFACT).toBe("artifact")
    expect(NodeTypeConstants.NOTE).toBe("note")
    expect(NodeTypeConstants.PROJECT).toBe("project")
    expect(NodeTypeConstants.TAG).toBe("tag")
    expect(NodeTypeConstants.TASK).toBe("task")
  })

  it("defines entity types", () => {
    expect(NodeTypeConstants.PERSON).toBe("person")
    expect(NodeTypeConstants.ORGANIZATION).toBe("organization")
    expect(NodeTypeConstants.LOCATION).toBe("location")
  })

  it("defines custom type", () => {
    expect(NodeTypeConstants.CUSTOM).toBe("custom")
  })

  it("has all expected constants", () => {
    const values = Object.values(NodeTypeConstants)
    expect(values.length).toBeGreaterThan(20)
  })
})

describe("EdgeTypeConstants", () => {
  it("defines core edge types", () => {
    expect(EdgeTypeConstants.CONTAINS).toBe("contains")
    expect(EdgeTypeConstants.PRODUCES).toBe("produces")
    expect(EdgeTypeConstants.DERIVES_FROM).toBe("derives_from")
    expect(EdgeTypeConstants.REFERENCES).toBe("references")
    expect(EdgeTypeConstants.BELONGS_TO).toBe("belongs_to")
    expect(EdgeTypeConstants.GENERATED).toBe("generated")
  })

  it("defines relationship edge types", () => {
    expect(EdgeTypeConstants.USES).toBe("uses")
    expect(EdgeTypeConstants.MENTIONS).toBe("mentions")
    expect(EdgeTypeConstants.RELATED_TO).toBe("related_to")
    expect(EdgeTypeConstants.SEQUENCES).toBe("sequences")
    expect(EdgeTypeConstants.CONTRIBUTES_TO).toBe("contributes_to")
    expect(EdgeTypeConstants.TRANSFORMS).toBe("transforms")
  })

  it("defines pinned edge type", () => {
    expect(EdgeTypeConstants.PINNED).toBe("pinned")
  })

  it("has all expected constants", () => {
    const values = Object.values(EdgeTypeConstants)
    expect(values.length).toBeGreaterThanOrEqual(15)
  })
})
