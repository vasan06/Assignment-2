"use client";

import { useState } from "react";
import { Search, X } from "lucide-react";

interface Props {
  onSearch: (query: string) => void;
  placeholder?: string;
}

export default function SearchBar({ onSearch, placeholder = "Search…" }: Props) {
  const [value, setValue] = useState("");

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value);
    onSearch(e.target.value);
  };

  const clear = () => {
    setValue("");
    onSearch("");
  };

  return (
    <div className="relative max-w-md">
      <Search
        size={16}
        className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none"
      />
      <input
        type="text"
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        className="w-full bg-surface-2 border border-border rounded-lg pl-10 pr-9 py-2.5 text-sm focus:outline-none focus:border-accent transition-colors placeholder:text-text-muted"
      />
      {value && (
        <button
          className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
          onClick={clear}
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}
