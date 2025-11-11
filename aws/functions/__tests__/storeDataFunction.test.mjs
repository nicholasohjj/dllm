import { describe, expect, it, vi, beforeEach } from "vitest";

const sendMock = vi.fn();

vi.mock("@aws-sdk/client-dynamodb", () => {
  return {
    DynamoDBClient: vi.fn(() => ({})),
  };
});

vi.mock("@aws-sdk/lib-dynamodb", () => {
  return {
    DynamoDBDocumentClient: {
      from: vi.fn(() => ({ send: sendMock })),
    },
    PutCommand: vi.fn((input) => ({ input, name: "PutCommand" })),
    UpdateCommand: vi.fn((input) => ({ input, name: "UpdateCommand" })),
  };
});

describe("storeDataFunction handler", () => {
  beforeEach(() => {
    sendMock.mockReset();
    process.env.DYNAMODB_TABLE = "TelemetryTable";
    process.env.MACHINE_STATUS_TABLE = "MachineStatusTable";
  });

  it("stores vibration payload and updates machine status when vibration is 1", async () => {
    sendMock.mockResolvedValueOnce({}).mockResolvedValueOnce({});

    const { handler } = await import("../storeDataFunction.mjs");
    const event = { machine_id: "RVREB-W1", vibration: 1 };
    const response = await handler(event);

    expect(response.statusCode).toBe(200);
    expect(sendMock).toHaveBeenCalledTimes(2);
    expect(sendMock.mock.calls[0][0]).toEqual(
      expect.objectContaining({
        name: "PutCommand",
        input: expect.objectContaining({
          TableName: "TelemetryTable",
          Item: event,
        }),
      })
    );
    expect(sendMock.mock.calls[1][0]).toEqual(
      expect.objectContaining({
        name: "UpdateCommand",
        input: expect.objectContaining({
          TableName: "MachineStatusTable",
          Key: { machineID: "RVREB-W1" },
        }),
      })
    );
  });

  it("skips status update when vibration is 0", async () => {
    sendMock.mockResolvedValueOnce({});

    const { handler } = await import("../storeDataFunction.mjs");
    const event = { machine_id: "RVREB-W1", vibration: 0 };
    await handler(event);

    expect(sendMock).toHaveBeenCalledTimes(1);
    expect(sendMock.mock.calls[0][0].name).toBe("PutCommand");
  });
});


