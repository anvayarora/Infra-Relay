import { forwardRef } from "react";
import {
  motion,
  type HTMLMotionProps,
  type Transition,
} from "framer-motion";
import { cn, spring } from "../../lib/utils";

const fallbackSpring: Transition = {
  type: "spring",
  stiffness: 300,
  damping: 30,
};

export type CardProps = Omit<HTMLMotionProps<"div">, "ref">;

const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      className,
      transition,
      layout = true,
      ...props
    },
    ref,
  ) => (
    <motion.div
      ref={ref}
      layout={layout}
      transition={transition ?? spring ?? fallbackSpring}
      className={cn("panel", className)}
      {...props}
    />
  ),
);

Card.displayName = "Card";

export interface CardHeaderProps
  extends React.HTMLAttributes<HTMLDivElement> {}

const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "flex items-start justify-between gap-4 border-b border-zinc-100 px-5 py-4 dark:border-zinc-900",
        className,
      )}
      {...props}
    />
  ),
);

CardHeader.displayName = "CardHeader";

export interface CardContentProps
  extends React.HTMLAttributes<HTMLDivElement> {}

const CardContent = forwardRef<HTMLDivElement, CardContentProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("p-5", className)}
      {...props}
    />
  ),
);

CardContent.displayName = "CardContent";

export interface CardFooterProps
  extends React.HTMLAttributes<HTMLDivElement> {}

const CardFooter = forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "flex items-center gap-3 border-t border-zinc-100 px-5 py-4 dark:border-zinc-900",
        className,
      )}
      {...props}
    />
  ),
);

CardFooter.displayName = "CardFooter";

export { Card, CardHeader, CardContent, CardFooter };
