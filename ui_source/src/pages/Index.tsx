import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowRight, Check, X } from "lucide-react";

const steps = [
  {
    number: "01",
    title: "Enter the problem",
    body: "Explore a sample problem from this demo bank. Arbitrary problem entry is not implemented.",
    visual: (
      <div className="bg-secondary border border-border p-6 md:p-8 w-full">
        <span className="text-xs uppercase tracking-wider text-muted-foreground block mb-4">
          Your problem
        </span>
        <p className="text-xl md:text-2xl text-foreground">
          Solve for x: 3x² − 12x + 9 = 0
        </p>
        <div className="mt-6 h-1 w-24 bg-primary" />
      </div>
    ),
  },
  {
    number: "02",
    title: "Show your work",
    body: "Enter your own solution, step by step. MathMentor AI reads it the way a tutor would.",
    visual: (
      <div className="bg-secondary border border-border p-6 md:p-8 w-full">
        <span className="text-xs uppercase tracking-wider text-muted-foreground block mb-4">
          Your solution
        </span>
        <ul className="space-y-3 text-lg md:text-xl text-foreground">
          <li>1. Factor out 3: 3(x² − 4x + 3) = 0</li>
          <li>2. Factor the quadratic: (x − 1)(x − 3) = 0</li>
          <li>3. So x = 1</li>
        </ul>
      </div>
    ),
  },
  {
    number: "03",
    title: "Get step-by-step feedback",
    body: "Each step is checked. The first wrong move is found, explained, and corrected — and your progress is tracked over time.",
    visual: (
      <div className="bg-secondary border border-border p-6 md:p-8 w-full space-y-4">
        <div className="flex items-start gap-3">
          <Check className="w-5 h-5 mt-1 text-primary shrink-0" />
          <p className="text-base md:text-lg text-foreground">
            Step 1 correct. Step 2 correct.
          </p>
        </div>
        <div className="flex items-start gap-3">
          <X className="w-5 h-5 mt-1 text-destructive shrink-0" />
          <p className="text-base md:text-lg text-foreground">
            Step 3: incomplete — one root is missing.
          </p>
        </div>
        <div className="border-l-2 border-primary pl-4">
          <p className="text-base md:text-lg text-primary">
            Both factors give solutions: x = 1 and x = 3. Check them back into
            the original equation.
          </p>
        </div>
      </div>
    ),
  },
];

const startOptions = [
  {
    to: "/analyze",
    label: "Analyze a problem",
    desc: "Jump straight into the workspace and get feedback on your solution.",
  },
  {
    to: "/about",
    label: "How MathMentor works",
    desc: "The idea behind the app, and how to reach the team.",
  },
  {
    to: "/mastery",
    label: "View your mastery",
    desc: "See progress by topic and explore detailed concept scores.",
  },
  {
    to: "/settings",
    label: "Settings",
    desc: "Manage your account and choose how MathMentor looks and feels.",
  },
];

const Index = () => {
  return (
    <main className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="min-h-screen flex flex-col justify-center px-4 md:px-6 pt-20">
        <div className="container mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="max-w-6xl"
          >
            <h1 className="heading-display text-[clamp(2.5rem,8vw,7rem)] leading-[0.9] mb-8">
              Solve it.
              <span className="text-primary"> Then understand it.</span>
            </h1>
          </motion.div>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="text-xl md:text-2xl text-muted-foreground max-w-2xl mt-12 mb-16"
          >
            MathMentor AI reviews your solution step by step, pinpoints exactly
            where things went wrong, explains how to fix it — and tracks your
            progress as you improve.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="flex flex-wrap items-center gap-8"
          >
            <Link
              to="/analyze"
              className="inline-flex items-center gap-4 text-xl font-semibold uppercase tracking-wider bg-primary text-primary-foreground px-10 py-5 hover:bg-primary/90 transition-colors group"
            >
              Start analyzing
              <ArrowRight className="w-6 h-6 group-hover:translate-x-2 transition-transform" />
            </Link>
            <Link
              to="/about"
              className="inline-flex items-center gap-4 text-xl font-semibold uppercase tracking-wider text-muted-foreground hover:text-primary transition-all group"
            >
              See how it works
              <ArrowRight className="w-6 h-6 group-hover:translate-x-2 transition-transform" />
            </Link>
          </motion.div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-32 px-4 md:px-6 border-t border-border">
        <div className="container mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="mb-24"
          >
            <span className="text-xs uppercase tracking-wider text-muted-foreground block mb-4">
              How it works
            </span>
            <h2 className="heading-display text-4xl md:text-6xl">
              Three steps to <span className="text-primary">mastery</span>
            </h2>
          </motion.div>

          <div className="space-y-24">
            {steps.map((step, index) => (
              <div
                key={step.number}
                className={`grid grid-cols-1 lg:grid-cols-12 gap-12 items-center ${
                  index % 2 === 1 ? "" : ""
                }`}
              >
                {/* Text */}
                <motion.div
                  initial={{ opacity: 0, x: index % 2 === 0 ? -20 : 20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.6 }}
                  viewport={{ once: true }}
                  className={`lg:col-span-5 ${
                    index % 2 === 1 ? "lg:order-2" : ""
                  }`}
                >
                  <span className="heading-display text-6xl md:text-7xl text-primary block mb-6">
                    {step.number}
                  </span>
                  <h3 className="heading-display text-3xl md:text-4xl mb-6">
                    {step.title}
                  </h3>
                  <p className="text-xl text-muted-foreground leading-relaxed">
                    {step.body}
                  </p>
                </motion.div>

                {/* Visual */}
                <motion.div
                  initial={{ opacity: 0, y: 40 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 0.15 }}
                  viewport={{ once: true }}
                  className={`lg:col-span-7 ${
                    index % 2 === 1 ? "lg:order-1" : ""
                  }`}
                >
                  {step.visual}
                </motion.div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Get Started Section */}
      <section className="py-32 px-4 md:px-6 border-t border-border">
        <div className="container mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="mb-16"
          >
            <span className="text-xs uppercase tracking-wider text-muted-foreground block mb-4">
              Get started
            </span>
            <h2 className="heading-display text-4xl md:text-6xl">
              Pick your <span className="text-primary">path</span>
            </h2>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
            {startOptions.map((option, index) => (
              <motion.div
                key={option.to}
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                viewport={{ once: true }}
              >
                <Link
                  to={option.to}
                  className="group flex flex-col h-full bg-secondary border border-border p-8 hover:border-primary transition-colors"
                >
                  <h3 className="heading-display text-2xl mb-4 group-hover:text-primary transition-colors">
                    {option.label}
                  </h3>
                  <p className="text-lg text-muted-foreground leading-relaxed flex-1">
                    {option.desc}
                  </p>
                  <span className="inline-flex items-center gap-3 mt-8 text-sm font-semibold uppercase tracking-wider text-foreground group-hover:text-primary transition-colors">
                    Go
                    <ArrowRight className="w-5 h-5 group-hover:translate-x-2 transition-transform" />
                  </span>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
};

export default Index;
