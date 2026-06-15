alter table public.size_measure_logs
    drop constraint if exists size_measure_logs_lan_do_check;

alter table public.size_measure_logs
    add constraint size_measure_logs_lan_do_check
    check (lan_do = any (array[1, 2, 3]));
