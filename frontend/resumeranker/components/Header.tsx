import React from 'react';

const Header: React.FC = () => {
  return (
    <header className="flex items-center justify-between whitespace-nowrap border-b border-solid border-gray-200 dark:border-border-dark px-4 sm:px-6 lg:px-10 py-3 bg-white dark:bg-background-dark/50 backdrop-blur-sm sticky top-0 z-50">
      <div className="flex items-center gap-4 text-black dark:text-white cursor-pointer" onClick={() => window.location.reload()}>
        <div className="text-primary size-6">
          <span className="material-symbols-outlined" style={{ fontSize: '24px' }}>auto_awesome</span>
        </div>
        <h2 className="text-lg font-bold leading-tight tracking-[-0.015em]">ResumeRanker</h2>
      </div>
      <nav className="hidden md:flex flex-1 justify-end gap-8">
        <div className="flex items-center gap-9">
          <a className="text-sm font-medium leading-normal text-gray-800 dark:text-white hover:text-primary transition-colors" href="#how-it-works">How It Works</a>
          <a className="text-sm font-medium leading-normal text-gray-800 dark:text-white hover:text-primary transition-colors" href="#pricing">Pricing</a>
          <a className="text-sm font-medium leading-normal text-gray-800 dark:text-white hover:text-primary transition-colors" href="#about">About</a>
        </div>
      </nav>
      <button className="md:hidden text-black dark:text-white">
        <span className="material-symbols-outlined">menu</span>
      </button>
    </header>
  );
};

export default Header;