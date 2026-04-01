-- =====================================================
-- MIGRATION: Chuyển mật khẩu RBAC từ hardcode sang Database
-- =====================================================

-- 1. Tạo bảng user_roles
CREATE TABLE IF NOT EXISTS user_roles (
    id SERIAL PRIMARY KEY,
    farm TEXT NOT NULL,
    team TEXT NOT NULL,
    password TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(farm, team)
);

-- 2. Seed dữ liệu từ RBAC_DB hiện tại
INSERT INTO user_roles (farm, team, password) VALUES
    -- Admin
    ('Admin', 'Quản trị viên', 'admin123'),
    -- Farm 126
    ('Farm 126', 'NT1', '6677028'),
    ('Farm 126', 'NT2', '040187'),
    ('Farm 126', 'Đội BVTV', '123'),
    ('Farm 126', 'Đội Thu Hoạch', '123'),
    ('Farm 126', 'Xưởng Đóng Gói', '123'),
    ('Farm 126', 'Quản lý farm', 'ql126'),
    -- Farm 157
    ('Farm 157', 'NT1', 'Trung@1985'),
    ('Farm 157', 'NT2', '0056'),
    ('Farm 157', 'Đội BVTV', '456'),
    ('Farm 157', 'Đội Thu Hoạch', '456'),
    ('Farm 157', 'Xưởng Đóng Gói', '456'),
    ('Farm 157', 'Quản lý farm', 'ql157'),
    -- Farm 195
    ('Farm 195', 'NT1', '789'),
    ('Farm 195', 'NT2', '789'),
    ('Farm 195', 'Đội BVTV', '789'),
    ('Farm 195', 'Đội Thu Hoạch', '789'),
    ('Farm 195', 'Xưởng Đóng Gói', '789'),
    ('Farm 195', 'Quản lý farm', 'ql195')
ON CONFLICT (farm, team) DO NOTHING;
