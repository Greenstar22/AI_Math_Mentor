import { motion } from "framer-motion";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { useAppearance } from "@/contexts/AppearanceContext";

const accountFields = [
  { label: "Full name", placeholder: "Your name", type: "text" },
  { label: "Email", placeholder: "you@example.com", type: "email" },
  { label: "School / class", placeholder: "Optional", type: "text" },
];

const Settings = () => {
  const { isDark, setIsDark } = useAppearance();

  return (
    <main className="min-h-screen bg-background px-4 pb-20 pt-32 md:px-6">
      <div className="container mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-16"
        >
          <h1 className="heading-display mb-8 text-[clamp(3rem,10vw,10rem)] leading-[0.85]">
            Settings
          </h1>
          <p className="max-w-2xl text-xl text-muted-foreground">
            Preview appearance controls and account placeholders in this design demo.
          </p>
        </motion.div>

        <motion.section
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="mb-20 max-w-3xl"
        >
          <h2 className="heading-display mb-2 text-3xl md:text-4xl">Display</h2>
          <p className="mb-8 text-muted-foreground">
            Choose the brightness that feels best for studying.
          </p>

          <div className="border border-border bg-secondary/50 normal-accent">
            <div className="flex items-center justify-between gap-6 p-6 md:p-8">
              <div className="flex min-w-0 items-start gap-4">
                {isDark ? (
                  <Moon className="mt-0.5 h-6 w-6 shrink-0 text-primary" />
                ) : (
                  <Sun className="mt-0.5 h-6 w-6 shrink-0 text-primary" />
                )}
                <div>
                  <p className="text-lg font-semibold text-foreground">
                    {isDark ? "Dark mode" : "Light mode"}
                  </p>
                  <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                    {isDark
                      ? "A low-glare workspace for comfortable studying."
                      : "A bright, crisp workspace for daytime study."}
                  </p>
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <span className="hidden text-xs uppercase tracking-wider text-muted-foreground sm:inline">
                  Light
                </span>
                <Switch
                  checked={isDark}
                  onCheckedChange={setIsDark}
                  aria-label="Switch between light and dark mode"
                />
                <span className="hidden text-xs uppercase tracking-wider text-muted-foreground sm:inline">
                  Dark
                </span>
              </div>
            </div>
          </div>
        </motion.section>

        <motion.section
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="max-w-3xl"
        >
          <h2 className="heading-display mb-2 text-3xl md:text-4xl">Account</h2>
          <p className="mb-8 text-muted-foreground">
            Account and password controls are placeholders. Only appearance is saved in this browser; use the Streamlit app for real accounts.
          </p>

          <div className="space-y-6 border border-border bg-secondary/50 p-6 md:p-8">
            {accountFields.map((field) => (
              <div key={field.label}>
                <label className="mb-2 block text-xs uppercase tracking-wider text-muted-foreground">
                  {field.label}
                </label>
                <input
                  type={field.type}
                  placeholder={field.placeholder}
                  className="w-full border border-border bg-background p-4 text-lg text-foreground transition-colors placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none"
                />
              </div>
            ))}

            <div className="space-y-6 border-t border-border pt-6">
              <span className="block text-xs uppercase tracking-wider text-muted-foreground">
                Change password
              </span>
              <input
                type="password"
                placeholder="Current password"
                className="w-full border border-border bg-background p-4 text-lg text-foreground transition-colors placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none"
              />
              <input
                type="password"
                placeholder="New password"
                className="w-full border border-border bg-background p-4 text-lg text-foreground transition-colors placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none"
              />
            </div>

            <div className="flex flex-wrap gap-4 pt-2">
              <Button className="h-auto rounded-none px-6 py-3 text-sm font-semibold uppercase tracking-wider">
                Save changes
              </Button>
              <Button
                variant="outline"
                className="h-auto rounded-none px-6 py-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground hover:border-destructive hover:text-destructive"
              >
                Sign out
              </Button>
            </div>
          </div>
        </motion.section>
      </div>
    </main>
  );
};

export default Settings;