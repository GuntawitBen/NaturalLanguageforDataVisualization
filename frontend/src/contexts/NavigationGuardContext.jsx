import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';

const NavigationGuardContext = createContext(null);

export function NavigationGuardProvider({ children }) {
  const [isBlocked, setIsBlocked] = useState(false);
  const [blockMessage, setBlockMessage] = useState('');
  const [onConfirmLeave, setOnConfirmLeave] = useState(null);

  // Use refs to access latest values in event handlers
  const isBlockedRef = useRef(isBlocked);
  const blockMessageRef = useRef(blockMessage);
  const onConfirmLeaveRef = useRef(onConfirmLeave);

  // Keep refs in sync
  useEffect(() => {
    isBlockedRef.current = isBlocked;
    blockMessageRef.current = blockMessage;
    onConfirmLeaveRef.current = onConfirmLeave;
  }, [isBlocked, blockMessage, onConfirmLeave]);

  // Push history state when blocking starts (not on mount)
  useEffect(() => {
    if (isBlocked) {
      window.history.pushState({ navigationGuard: true }, '', window.location.href);
    }
  }, [isBlocked]);

  // Handle browser close/refresh and back button
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (isBlockedRef.current) {
        e.preventDefault();
        e.returnValue = blockMessageRef.current;
        return e.returnValue;
      }
    };

    const handleUnload = () => {
      if (isBlockedRef.current && onConfirmLeaveRef.current) {
        onConfirmLeaveRef.current();
      }
    };

    // Handle browser back/forward buttons
    let isNavigatingAway = false;

    const handlePopState = (e) => {
      // Skip if not blocked or already navigating away
      if (!isBlockedRef.current || isNavigatingAway) return;

      // Push state to cancel the back navigation
      window.history.pushState({ navigationGuard: true }, '', window.location.href);

      const confirmed = window.confirm(blockMessageRef.current);
      if (confirmed) {
        if (onConfirmLeaveRef.current) {
          onConfirmLeaveRef.current();
        }
        // Set flag to allow navigation
        isNavigatingAway = true;
        // Go back twice: once for state we just pushed, once for actual navigation
        window.history.go(-2);
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    window.addEventListener('unload', handleUnload);
    window.addEventListener('popstate', handlePopState);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      window.removeEventListener('unload', handleUnload);
      window.removeEventListener('popstate', handlePopState);
    };
  }, []);

  const blockNavigation = useCallback((message, onLeaveCallback) => {
    setIsBlocked(true);
    setBlockMessage(message || 'Are you sure you want to leave? All unsaved changes will be lost.');
    // Store callback as a function that returns the callback to avoid React setState issues
    setOnConfirmLeave(() => onLeaveCallback);
  }, []);

  const unblockNavigation = useCallback(() => {
    setIsBlocked(false);
    setBlockMessage('');
    setOnConfirmLeave(null);
  }, []);

  const confirmNavigation = useCallback((proceedCallback) => {
    if (!isBlocked) {
      proceedCallback();
      return;
    }

    const confirmed = window.confirm(blockMessage);
    if (confirmed) {
      // Call the cleanup callback if provided
      if (onConfirmLeave) {
        onConfirmLeave();
      }
      unblockNavigation();
      proceedCallback();
    }
  }, [isBlocked, blockMessage, onConfirmLeave, unblockNavigation]);

  return (
    <NavigationGuardContext.Provider value={{
      isBlocked,
      blockMessage,
      blockNavigation,
      unblockNavigation,
      confirmNavigation,
    }}>
      {children}
    </NavigationGuardContext.Provider>
  );
}

export function useNavigationGuard() {
  const context = useContext(NavigationGuardContext);
  if (!context) {
    throw new Error('useNavigationGuard must be used within a NavigationGuardProvider');
  }
  return context;
}
