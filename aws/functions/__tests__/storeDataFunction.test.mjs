import { describe, expect, it, vi, beforeEach } from "vitest";

const sendMock = vi.fn();
const lambdaSendMock = vi.fn();

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

vi.mock("@aws-sdk/client-lambda", () => {
  return {
    LambdaClient: vi.fn(() => ({ send: lambdaSendMock })),
    InvokeCommand: vi.fn((input) => ({ input, name: "InvokeCommand" })),
  };
});

describe("storeDataFunction handler", () => {
  beforeEach(() => {
    sendMock.mockReset();
    lambdaSendMock.mockReset();
    process.env.DYNAMODB_TABLE = "TelemetryTable";
    process.env.STATE_MACHINE_FUNCTION = "updateMachineStateFunction";
  });

  it("stores vibration payload and invokes state machine function when vibration is 1", async () => {
    sendMock.mockResolvedValueOnce({});
    lambdaSendMock.mockResolvedValueOnce({});

    const { handler } = await import("../storeDataFunction.mjs");
    const event = { machine_id: "RVREB-W1", vibration: 1 };
    const response = await handler(event);

    expect(response.statusCode).toBe(200);
    expect(sendMock).toHaveBeenCalledTimes(1);
    expect(sendMock.mock.calls[0][0]).toEqual(
      expect.objectContaining({
        name: "PutCommand",
        input: expect.objectContaining({
          TableName: "TelemetryTable",
          Item: expect.objectContaining({
            machine_id: "RVREB-W1",
            vibration: 1,
          }),
        }),
      })
    );
    expect(lambdaSendMock).toHaveBeenCalledTimes(1);
    expect(lambdaSendMock.mock.calls[0][0]).toEqual(
      expect.objectContaining({
        name: "InvokeCommand",
        input: expect.objectContaining({
          FunctionName: "updateMachineStateFunction",
          InvocationType: "Event",
        }),
      })
    );
  });

  it("stores vibration payload and invokes state machine function when vibration is 0", async () => {
    sendMock.mockResolvedValueOnce({});
    lambdaSendMock.mockResolvedValueOnce({});

    const { handler } = await import("../storeDataFunction.mjs");
    const event = { machine_id: "RVREB-W1", vibration: 0 };
    const response = await handler(event);

    expect(response.statusCode).toBe(200);
    expect(sendMock).toHaveBeenCalledTimes(1);
    expect(sendMock.mock.calls[0][0].name).toBe("PutCommand");
    expect(lambdaSendMock).toHaveBeenCalledTimes(1);
  });
});


