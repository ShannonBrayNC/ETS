// Compile against the installed tarball's advertised declarations, not src imports.
import { EtsClient, type EtsClientOptions, type EventCommitReceipt } from "@lanternprotocol/ets-sdk";

const options: EtsClientOptions = { baseUrl: "https://ets.example/" };
const client = new EtsClient(options);
const capture: (event: unknown) => Promise<EventCommitReceipt> = (event) => client.capture(event);
void capture; // Type checking only; no network operation is performed.
