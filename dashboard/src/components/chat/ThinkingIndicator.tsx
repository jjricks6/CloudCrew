import { motion } from "framer-motion";

export function ThinkingIndicator() {
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground">
        Project Manager
      </p>
      <div className="flex items-center gap-1">
        <span className="text-sm text-muted-foreground">Thinking</span>
        <div className="flex gap-0.5">
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              className="inline-block h-1 w-1 rounded-full bg-muted-foreground"
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{
                duration: 1.2,
                repeat: Infinity,
                delay: i * 0.2,
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
