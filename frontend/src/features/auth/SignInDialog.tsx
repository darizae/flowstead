import { useState, type FormEvent } from 'react';
import { Button, Dialog, DialogContent, DialogDescription, DialogTitle } from '@darizae/marisma';

export interface SignInDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Returns true on successful sign-in (dialog closes), false on failure. */
  onSignIn: (email: string, password: string) => Promise<boolean>;
}

export function SignInDialog({ open, onOpenChange, onSignIn }: SignInDialogProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [signingIn, setSigningIn] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reset = () => { setPassword(''); setError(null); setSigningIn(false); };
  const handleOpenChange = (next: boolean) => {
    if (next) { setEmail(''); reset(); } else { reset(); }
    onOpenChange(next);
  };
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!email || !password) return;
    setSigningIn(true);
    setError(null);
    const ok = await onSignIn(email, password);
    if (ok) {
      handleOpenChange(false);
    } else {
      // Provider error details can contain internal auth configuration data;
      // present a stable, non-enumerating failure to unauthenticated visitors.
      setPassword('');
      setSigningIn(false);
      setError('Sign in failed. Check your credentials and try again.');
    }
  };
  return <Dialog open={open} onOpenChange={handleOpenChange}>
    <DialogContent className="auth-modal-content" showCloseButton={false} aria-labelledby="sign-in-title" aria-describedby="sign-in-description">
      <DialogTitle id="sign-in-title">Sign in</DialogTitle>
      <DialogDescription id="sign-in-description">Sign in with your invited operator credentials. No account creation; contact your administrator for access.</DialogDescription>
      <form className="auth-form" onSubmit={submit} noValidate>
        <label htmlFor="sign-in-email">Email</label>
        <input id="sign-in-email" name="email" type="email" autoComplete="email" autoFocus={open} value={email} onChange={(event) => setEmail(event.target.value)} aria-label="Email" />
        <label htmlFor="sign-in-password">Password</label>
        <input id="sign-in-password" name="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} aria-label="Password" />
        {error && <p className="auth-error" role="alert" data-testid="sign-in-error">{error}</p>}
        <div className="auth-actions">
          <Button type="button" variant="secondary" size="small" onClick={() => handleOpenChange(false)}>Cancel</Button>
          <Button type="submit" variant="primary" size="small" loading={signingIn} disabled={signingIn || !email || !password}>Sign in</Button>
        </div>
      </form>
    </DialogContent>
  </Dialog>;
}