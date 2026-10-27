/** Flexible API record envelope; request shapes are validated by backend Pydantic models. */
export type Row = Record<string, any>;
export type Field = {
    key: string;
    label: string;
    type?: string;
    options?: (string | { value: string; label: string })[];
    required?: boolean;
    hint?: string;
    value?: any;
};
