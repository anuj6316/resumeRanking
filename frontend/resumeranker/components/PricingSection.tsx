import React from 'react';

const PricingSection: React.FC = () => {
  const plans = [
    {
      name: "Starter",
      price: "$0",
      period: "/month",
      description: "Perfect for small businesses and startups hiring occasionally.",
      features: [
        "Up to 10 resume parses per month",
        "Basic ranking algorithm",
        "Email support",
        "1 user account"
      ],
      cta: "Get Started Free",
      highlight: false
    },
    {
      name: "Pro",
      price: "$49",
      period: "/month",
      description: "Ideal for growing teams with regular hiring needs.",
      features: [
        "Up to 100 resume parses per month",
        "Advanced AI ranking & summaries",
        "Priority email support",
        "5 user accounts",
        "Export reports to PDF/CSV"
      ],
      cta: "Start Free Trial",
      highlight: true
    },
    {
      name: "Enterprise",
      price: "Custom",
      period: "",
      description: "For large organizations requiring high volume and custom integrations.",
      features: [
        "Unlimited resume parses",
        "Custom ranking criteria",
        "Dedicated account manager",
        "SSO & Custom Integrations",
        "API Access"
      ],
      cta: "Contact Sales",
      highlight: false
    }
  ];

  return (
    <section id="pricing" className="py-20 px-4 sm:px-6 lg:px-8 bg-background-light dark:bg-background-dark">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">Simple, Transparent Pricing</h2>
          <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            Choose the plan that best fits your hiring volume. No hidden fees.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {plans.map((plan, index) => (
            <div 
              key={index}
              className={`relative rounded-2xl p-8 transition-all duration-300 flex flex-col ${
                plan.highlight 
                  ? 'bg-white dark:bg-surface-dark border-2 border-primary shadow-xl scale-105 z-10' 
                  : 'bg-white dark:bg-surface-dark border border-gray-200 dark:border-border-dark hover:border-primary/50'
              }`}
            >
              {plan.highlight && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-primary text-white px-4 py-1 rounded-full text-sm font-bold shadow-md">
                  Most Popular
                </div>
              )}
              
              <div className="mb-8">
                <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">{plan.name}</h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-extrabold text-gray-900 dark:text-white">{plan.price}</span>
                  <span className="text-gray-500 dark:text-gray-400 font-medium">{plan.period}</span>
                </div>
                <p className="mt-4 text-gray-600 dark:text-gray-400 text-sm">{plan.description}</p>
              </div>

              <ul className="space-y-4 mb-8 flex-1">
                {plan.features.map((feature, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <span className="material-symbols-outlined text-green-500 text-xl shrink-0">check</span>
                    <span className="text-gray-700 dark:text-gray-300 text-sm">{feature}</span>
                  </li>
                ))}
              </ul>

              <button className={`w-full py-3 px-4 rounded-lg font-bold text-sm transition-colors ${
                plan.highlight
                  ? 'bg-primary text-white hover:bg-blue-600 shadow-lg shadow-primary/25'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}>
                {plan.cta}
              </button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default PricingSection;