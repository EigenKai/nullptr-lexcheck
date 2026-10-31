// English catalogue. Each screen group keeps its own file so the strings
// stay next to the components that use them.
import shell from "./en-shell.js";
import chat from "./en-chat.js";
import review from "./en-review.js";
import updates from "./en-updates.js";
import tasks from "./en-tasks.js";

export default { ...shell, ...chat, ...review, ...updates, ...tasks };
