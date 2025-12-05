import React from 'react';

const Footer: React.FC = () => {
  return (
    <footer className="border-t border-gray-200 dark:border-border-dark mt-auto py-8 px-4 sm:px-6 lg:px-10">
      <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
        <p className="text-sm text-gray-500 dark:text-gray-400">© 2024 ResumeRanker. All rights reserved.</p>
        <div className="flex gap-4">
          <a className="text-sm text-gray-500 dark:text-gray-400 hover:text-primary" href="#">Privacy Policy</a>
          <a className="text-sm text-gray-500 dark:text-gray-400 hover:text-primary" href="#">Terms of Service</a>
          <a className="text-sm text-gray-500 dark:text-gray-400 hover:text-primary" href="#">Contact</a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;