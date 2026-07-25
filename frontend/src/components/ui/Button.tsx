import { forwardRef } from "react";
import {
  motion,
  type HTMLMotionProps,
  type Transition,
} from "framer-motion";
import { cn, spring } from "../../lib/utils";

export type ButtonVariant =
  | "primary"
  | "default"
  | "secondary"
  | "outline"
  | "ghost"
  | "danger"
  | "destructive";

export type ButtonSize =
  | "sm"
  | "md"
  | "default"
  | "lg"
  | "icon";

export interface ButtonProps
  extends Omit<HTMLMotionProps<"button">, "ref" | "children"> {
  children?: React.ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

const fallbackSpring: Transition = {
  type: "spring",
  stiffness: 300,
  damping: 30,
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      loading = false,
      disabled,
      children,
      type = "button",
      whileTap,
      transition,
      ...props
    },
    ref,
  ) => {
    const isPrimary = variant === "primary" || variant === "default";
    const isSecondary = variant === "secondary" || variant === "outline";
    const isDanger =
      variant === "danger" || variant === "destructive";

    const isDefaultSize = size === "md" || size === "default";

    return (
      <motion.button
        ref={ref}
        type={type}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        whileTap={whileTap ?? { scale: 0.98 }}
        transition={transition ?? spring ?? fallbackSpring}
        className={cn(
          "focus-ring inline-flex items-center justify-center gap-2 rounded-lg",
          "whitespace-nowrap text-sm font-medium transition-colors",
          "disabled:pointer-events-none disabled:opacity-50",

          isPrimary &&
            "bg-zinc-950 text-white hover:bg-zinc-800 dark:bg-white dark:text-zinc-950 dark:hover:bg-zinc-200",

          isSecondary &&
            "border border-zinc-200 bg-white text-zinc-800 hover:bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-100 dark:hover:bg-zinc-900",

          variant === "ghost" &&
            "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-900",

          isDanger &&
            "bg-red-600 text-white hover:bg-red-500 dark:bg-red-600 dark:hover:bg-red-500",

          size === "sm" && "h-8 px-3 text-xs",
          isDefaultSize && "h-9 px-4",
          size === "lg" && "h-11 px-8",
          size === "icon" && "h-9 w-9 p-0",

          className,
        )}
        {...props}
      >
        {loading && (
          <span
            aria-hidden="true"
            className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-r-transparent"
          />
        )}

        {children}
      </motion.button>
    );
  },
);

Button.displayName = "Button";

export { Button };
