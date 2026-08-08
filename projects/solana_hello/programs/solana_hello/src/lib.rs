use anchor_lang::prelude::*;

declare_id!("7NRJP2DUWUkaAGVPNvK1GESQT48FJJXcESrX1CWDC8KB");

#[program]
pub mod solana_hello {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
        msg!("Hello, World!");
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize {}
