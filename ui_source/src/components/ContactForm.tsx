import { useState } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";

const TOPICS = [
  { value: "feedback", label: "Feedback on the app" },
  { value: "idea", label: "Feature idea" },
  { value: "bug", label: "Something's broken" },
  { value: "collab", label: "Collaboration / business" },
] as const;

const ContactForm = () => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    topic: "feedback",
    message: "",
  });
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    // Simulate form submission
    await new Promise((resolve) => setTimeout(resolve, 1000));

    toast({
      title: "Demo form validated.",
      description: "This is a local demonstration. No contact message was sent.",
    });

    setFormData({ name: "", email: "", topic: "feedback", message: "" });
    setIsSubmitting(false);
  };

  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  return (
    <motion.form
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      onSubmit={handleSubmit}
      className="space-y-8 max-w-xl"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="space-y-2">
          <label
            htmlFor="name"
            className="text-xs uppercase tracking-wider text-muted-foreground"
          >
            Name
          </label>
          <Input
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            required
            className="bg-secondary border-border text-foreground placeholder:text-muted-foreground h-14 text-lg"
            placeholder="Your name"
          />
        </div>

        <div className="space-y-2">
          <label
            htmlFor="email"
            className="text-xs uppercase tracking-wider text-muted-foreground"
          >
            Email
          </label>
          <Input
            id="email"
            name="email"
            type="email"
            value={formData.email}
            onChange={handleChange}
            required
            className="bg-secondary border-border text-foreground placeholder:text-muted-foreground h-14 text-lg"
            placeholder="your@email.com"
          />
        </div>
      </div>

      <div className="space-y-2">
        <label
          htmlFor="topic"
          className="text-xs uppercase tracking-wider text-muted-foreground"
        >
          What's this about?
        </label>
        <select
          id="topic"
          name="topic"
          value={formData.topic}
          onChange={handleChange}
          className="w-full h-14 text-lg bg-secondary border border-border text-foreground rounded-md px-3 focus:outline-none focus:ring-2 focus:ring-ring"
        >
          {TOPICS.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-2">
        <label
          htmlFor="message"
          className="text-xs uppercase tracking-wider text-muted-foreground"
        >
          Message
        </label>
        <Textarea
          id="message"
          name="message"
          value={formData.message}
          onChange={handleChange}
          required
          className="bg-secondary border-border text-foreground placeholder:text-muted-foreground min-h-[200px] text-lg resize-none"
          placeholder="One line is enough — the good, the bad, or the idea."
        />
      </div>

      <Button
        type="submit"
        disabled={isSubmitting}
        className="w-full h-16 text-lg font-semibold uppercase tracking-wider bg-primary hover:bg-primary/90 text-primary-foreground"
      >
        {isSubmitting ? "Validating..." : "Validate demo form"}
      </Button>
    </motion.form>
  );
};

export default ContactForm;
