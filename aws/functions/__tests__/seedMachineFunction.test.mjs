import { beforeEach, describe, expect, it, vi } from "vitest";

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
    BatchWriteCommand: vi.fn((input) => ({ input, name: "BatchWriteCommand" })),
  };
});

describe("seedMachineFunction handler", () => {
  beforeEach(() => {
    sendMock.mockReset();
    process.env.MACHINE_STATUS_TABLE = "MachineStatusTable";
  });

  it("batches generated machines into DynamoDB", async () => {
    sendMock.mockResolvedValue({});

    const { handler } = await import("../seedMachineFunction.mjs");
    const response = await handler();

    expect(response.statusCode).toBe(200);
    expect(sendMock).toHaveBeenCalled();
    const command = sendMock.mock.calls[0][0];
    expect(command.name).toBe("BatchWriteCommand");
    const requestItems = command.input.RequestItems.MachineStatusTable;
    expect(requestItems).toHaveLength(14);
  });
});


