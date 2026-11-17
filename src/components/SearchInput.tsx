import React from "react";

interface SearchInputProps {
  id: string;
  label: string;
  testId: string;
  clearTestId: string;
  clearAriaLabel: string;
  value: string;
  onChange: (value: string) => void;
  onClear?: () => void;
  placeholder: string;
  className?: string;
}

/**
 * Campo de busca textual reutilizável com ícone de lupa e botão acessível de limpeza.
 */
export const SearchInput: React.FC<SearchInputProps> = ({
  id,
  label,
  testId,
  clearTestId,
  clearAriaLabel,
  value,
  onChange,
  onClear,
  placeholder,
  className = "",
}) => {
  return (
    <div className={`relative ${className}`}>
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      <span className="absolute inset-y-0 left-0 flex items-center pl-2.5 pointer-events-none text-slate-400">
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
      </span>
      <input
        id={id}
        type="text"
        data-testid={testId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full pl-8 pr-8 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 text-slate-800 placeholder-slate-400"
      />
      {value.trim().length > 0 && (
        <button
          type="button"
          data-testid={clearTestId}
          onClick={() => (onClear ? onClear() : onChange(""))}
          aria-label={clearAriaLabel}
          className="absolute inset-y-0 right-0 flex items-center pr-2 text-slate-400 hover:text-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 rounded"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      )}
    </div>
  );
};
