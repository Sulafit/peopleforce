import { actionTypes } from "./actions";
import { blockTypes } from "./blocks";
import { documentTypes } from "./documents";

export const schemaTypes = [...documentTypes, ...blockTypes, ...actionTypes];
